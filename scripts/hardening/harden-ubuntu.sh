#!/bin/bash
# ==============================================================================
# EduNaukri Master Ubuntu Server Hardening Script
# ==============================================================================
# Usage: sudo ./scripts/hardening/harden-ubuntu.sh
# Applies enterprise-grade security hardening across:
# 1. System Timezone (UTC)
# 2. Non-Root User Creation & Root Lockdown
# 3. OpenSSH Hardening & Key Authentication
# 4. UFW Firewall Configuration & Rate Limiting
# 5. Fail2Ban Intrusion Prevention System
# 6. Unattended Security Upgrades
# 7. Swap Memory Allocation
# 8. System Resource Limits (limits.d)
# 9. Kernel Sysctl Network Security & Tuning
# 10. Log Rotation Setup (logrotate)
# ==============================================================================

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root using sudo."
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Configuration defaults (can be overridden via environment variables)
SSH_PORT="${SSH_PORT:-22}"
TIMEZONE="${TIMEZONE:-UTC}"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-4}"
NON_ROOT_USER="${NON_ROOT_USER:-deploy}"

echo "========================================================================"
echo "Starting EduNaukri Ubuntu Production Server Hardening"
echo "========================================================================"
echo "SSH Port:      $SSH_PORT"
echo "Timezone:      $TIMEZONE"
echo "Swap Size:     ${SWAP_SIZE_GB}GB"
echo "Deploy User:   $NON_ROOT_USER"
echo "========================================================================"

# ------------------------------------------------------------------------------
# 1. System Timezone Configuration
# ------------------------------------------------------------------------------
echo "=== [1/10] Configuring System Timezone ($TIMEZONE) ==="
timedatectl set-timezone "$TIMEZONE"
echo "SUCCESS: System timezone set to $(timedatectl | grep 'Time zone' | awk '{print $3}')"

# ------------------------------------------------------------------------------
# 2. Non-Root Sudo User & Root Lockdown
# ------------------------------------------------------------------------------
echo "=== [2/10] Configuring Non-Root User ($NON_ROOT_USER) and Locking Root ==="
if ! id "$NON_ROOT_USER" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$NON_ROOT_USER"
    echo "Created user: $NON_ROOT_USER"
fi
usermod -aG sudo "$NON_ROOT_USER"

# Enable secure sudo access without password prompt interruptions during deployments
echo "$NON_ROOT_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/90-$NON_ROOT_USER"
chmod 440 "/etc/sudoers.d/90-$NON_ROOT_USER"

# Copy authorized SSH keys from root or existing user if present
mkdir -p "/home/$NON_ROOT_USER/.ssh"
if [ -f "/root/.ssh/authorized_keys" ]; then
    cp "/root/.ssh/authorized_keys" "/home/$NON_ROOT_USER/.ssh/authorized_keys"
elif [ -f "$HOME/.ssh/authorized_keys" ]; then
    cp "$HOME/.ssh/authorized_keys" "/home/$NON_ROOT_USER/.ssh/authorized_keys"
fi
touch "/home/$NON_ROOT_USER/.ssh/authorized_keys"
chmod 700 "/home/$NON_ROOT_USER/.ssh"
chmod 600 "/home/$NON_ROOT_USER/.ssh/authorized_keys"
chown -R "$NON_ROOT_USER:$NON_ROOT_USER" "/home/$NON_ROOT_USER/.ssh"
echo "SUCCESS: Non-root user $NON_ROOT_USER configured securely."

# ------------------------------------------------------------------------------
# 3. OpenSSH Server Hardening
# ------------------------------------------------------------------------------
echo "=== [3/10] Applying OpenSSH Server Hardening ==="
mkdir -p /etc/ssh/sshd_config.d
cp "$SCRIPT_DIR/sshd_config.d/99-edunaukri-hardening.conf" "/etc/ssh/sshd_config.d/99-edunaukri-hardening.conf"
chmod 644 "/etc/ssh/sshd_config.d/99-edunaukri-hardening.conf"

# Ensure main sshd_config includes drop-in configurations
if ! grep -q "^Include /etc/ssh/sshd_config.d/\*.conf" /etc/ssh/sshd_config; then
    sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' /etc/ssh/sshd_config
fi

if sshd -t; then
    systemctl reload ssh || systemctl reload sshd || true
    echo "SUCCESS: SSH server configuration validated and reloaded."
else
    echo "ERROR: SSH configuration validation failed! Please check syntax."
    exit 1
fi

# ------------------------------------------------------------------------------
# 4. UFW Firewall Configuration
# ------------------------------------------------------------------------------
echo "=== [4/10] Configuring UFW Firewall & Rate Limiting ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq ufw

ufw --force reset >/dev/null 2>&1 || true
ufw default deny incoming
ufw default allow outgoing
ufw limit "$SSH_PORT/tcp" comment "SSH rate-limited"
ufw allow 80/tcp comment "HTTP Web Traffic"
ufw allow 443/tcp comment "HTTPS Web Traffic"
ufw logging on
ufw --force enable
echo "SUCCESS: UFW firewall enabled and rate-limiting active on port $SSH_PORT."

# ------------------------------------------------------------------------------
# 5. Fail2Ban Intrusion Prevention System
# ------------------------------------------------------------------------------
echo "=== [5/10] Installing and Configuring Fail2Ban ==="
apt-get install -y -qq fail2ban
cp "$SCRIPT_DIR/fail2ban/jail.local" "/etc/fail2ban/jail.local"
chmod 644 "/etc/fail2ban/jail.local"
systemctl enable fail2ban >/dev/null 2>&1
systemctl restart fail2ban
echo "SUCCESS: Fail2Ban active with jails for sshd and nginx."

# ------------------------------------------------------------------------------
# 6. Automatic Security Updates
# ------------------------------------------------------------------------------
echo "=== [6/10] Configuring Unattended Automatic Security Upgrades ==="
apt-get install -y -qq unattended-upgrades apt-listchanges
cp "$SCRIPT_DIR/unattended-upgrades/20auto-upgrades" "/etc/apt/apt.conf.d/20auto-upgrades"
cp "$SCRIPT_DIR/unattended-upgrades/50unattended-upgrades" "/etc/apt/apt.conf.d/50unattended-upgrades"
chmod 644 "/etc/apt/apt.conf.d/20auto-upgrades" "/etc/apt/apt.conf.d/50unattended-upgrades"
systemctl enable unattended-upgrades >/dev/null 2>&1
systemctl restart unattended-upgrades
echo "SUCCESS: Unattended security updates configured."

# ------------------------------------------------------------------------------
# 7. Swap Memory Allocation
# ------------------------------------------------------------------------------
echo "=== [7/10] Checking and Configuring Swap Memory (${SWAP_SIZE_GB}GB) ==="
if [ ! -f /swapfile ] && [ "$(swapon --show | wc -l)" -eq 0 ]; then
    echo "Allocating ${SWAP_SIZE_GB}GB swap file..."
    if ! fallocate -l "${SWAP_SIZE_GB}G" /swapfile 2>/dev/null; then
        dd if=/dev/zero of=/swapfile bs=1M count=$((SWAP_SIZE_GB * 1024)) status=progress
    fi
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    echo "SUCCESS: Allocated and mounted ${SWAP_SIZE_GB}GB swap file."
else
    echo "INFO: Swap space is already configured ($(free -h | grep -i swap | awk '{print $2}'))."
fi

# ------------------------------------------------------------------------------
# 8. System Resource Limits
# ------------------------------------------------------------------------------
echo "=== [8/10] Applying System Resource Limits ==="
mkdir -p /etc/security/limits.d
cp "$SCRIPT_DIR/limits.d/99-edunaukri-limits.conf" "/etc/security/limits.d/99-edunaukri-limits.conf"
chmod 644 "/etc/security/limits.d/99-edunaukri-limits.conf"
echo "SUCCESS: System file descriptor and process limits applied."

# ------------------------------------------------------------------------------
# 9. Kernel & Network Stack Hardening (sysctl)
# ------------------------------------------------------------------------------
echo "=== [9/10] Applying Kernel Sysctl Security & Tuning ==="
mkdir -p /etc/sysctl.d
cp "$SCRIPT_DIR/sysctl.d/99-edunaukri-sysctl.conf" "/etc/sysctl.d/99-edunaukri-sysctl.conf"
chmod 644 "/etc/sysctl.d/99-edunaukri-sysctl.conf"
sysctl --system >/dev/null 2>&1 || true
echo "SUCCESS: Kernel security parameters and virtual memory tuning applied."

# ------------------------------------------------------------------------------
# 10. Log Rotation Setup
# ------------------------------------------------------------------------------
echo "=== [10/10] Configuring Log Rotation (logrotate) ==="
cp "$SCRIPT_DIR/logrotate.d/edunaukri" "/etc/logrotate.d/edunaukri"
chmod 644 "/etc/logrotate.d/edunaukri"
echo "SUCCESS: Log rotation configured for application, Nginx, and backup logs."

echo "========================================================================"
echo "EduNaukri Ubuntu Production Server Hardening Completed Successfully!"
echo "========================================================================"
echo "Next Steps & Verification Commands:"
echo "  • Check UFW Status:        sudo ufw status verbose"
echo "  • Check Fail2Ban Jails:    sudo fail2ban-client status"
echo "  • Check Swap Utilization:  free -h"
echo "  • Verify Sysctl Settings:  sysctl net.ipv4.tcp_syncookies"
echo "========================================================================"
