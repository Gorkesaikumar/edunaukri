# EduNaukri Ubuntu Server Production Hardening Suite

This directory (`scripts/hardening`) contains an enterprise-grade, automated, and idempotent hardening suite for preparing fresh **Ubuntu 22.04 LTS / 24.04 LTS** production hosts running the EduNaukri Docker stack.

---

## 🛡️ What This Hardening Suite Configures

| Component | Configuration File | Purpose & Hardening Details |
| :--- | :--- | :--- |
| **1. Timezone** | `timedatectl` | Sets the server system clock to **UTC** to guarantee unified timestamp alignment across Nginx, Django, Celery, and automated backups. |
| **2. Non-Root Sudo User** | `useradd`, `sudoers.d` | Creates a dedicated deployment user (`deploy` by default), sets up passwordless sudo for automated CI/CD deployments, and locks direct root access. |
| **3. OpenSSH Hardening** | `sshd_config.d/99-edunaukri-hardening.conf` | Disables root login (`PermitRootLogin no`), enforces SSH keys only (`PasswordAuthentication no`), limits auth retries (`MaxAuthTries 3`), and requires modern cryptography (ChaCha20-Poly1305, AES-GCM, Curve25519). |
| **4. UFW Firewall** | `ufw` | Denies all incoming traffic by default, allows outgoing traffic, rate-limits SSH (`ufw limit ssh`), allows HTTP (80) & HTTPS (443), and enables full audit logging. |
| **5. Fail2Ban IPS** | `fail2ban/jail.local` | Actively bans brute-force and vulnerability scanners across SSH (`maxretry = 3`), Nginx HTTP authentication, and automated bot directory enumeration (`[nginx-botsearch]`). |
| **6. Automatic Security Updates** | `unattended-upgrades/*` | Configures unattended, automatic daily installation of critical Ubuntu security patches without rebooting production database or web containers during peak hours. |
| **7. Swap Memory** | `/swapfile`, `/etc/fstab` | Automatically checks for and creates a **4GB swap file** (configurable) tuned with low swappiness (`vm.swappiness = 10`) to prevent out-of-memory (OOM) killer crashes under heavy load spikes. |
| **8. System Limits** | `limits.d/99-edunaukri-limits.conf` | Increases file descriptor limits (`nofile 1048576`) and maximum processes (`nproc 65535`) to support thousands of concurrent Docker sockets and Nginx connections. |
| **9. Kernel Sysctl Tuning** | `sysctl.d/99-edunaukri-sysctl.conf` | Enables SYN cookie flood protections, blocks ICMP redirects and source routing, logs martians, and increases `fs.inotify.max_user_watches` for Docker volumes. |
| **10. Log Rotation** | `logrotate.d/edunaukri` | Automatically rotates, compresses (`gzip`), and trims application, Nginx, and backup log files every 30 days (`copytruncate` prevents process disruption). |

---

## 🚀 One-Command Server Hardening Execution

To execute the full hardening suite on your fresh Ubuntu production host:

```bash
# Make the master script executable and run with root privileges
chmod +x scripts/hardening/harden-ubuntu.sh
sudo ./scripts/hardening/harden-ubuntu.sh
```

### Customizing Defaults via Environment Variables
If you run SSH on a custom port or desire a different swap allocation, pass environment variables directly:
```bash
sudo SSH_PORT=2222 TIMEZONE=UTC SWAP_SIZE_GB=8 NON_ROOT_USER=deploy ./scripts/hardening/harden-ubuntu.sh
```

---

## 🔍 Verification & Diagnostics

After running the script, verify that your server is secured and tuned:

```bash
# 1. Check UFW Firewall rules and rate limiting status
sudo ufw status verbose

# 2. Check Fail2Ban active jails and banned IP list
sudo fail2ban-client status
sudo fail2ban-client status sshd

# 3. Check Swap Memory allocation and swappiness
free -h
sysctl vm.swappiness

# 4. Check OpenSSH Configuration validation
sudo sshd -T | grep -E "(permitrootlogin|passwordauthentication|pubkeyauthentication)"

# 5. Check System Limits
ulimit -n
```
