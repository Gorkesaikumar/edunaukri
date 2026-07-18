/**
 * EduNaukri Super Admin Dashboard — Interactive Client-Side Logic
 */

document.addEventListener("DOMContentLoaded", () => {
    initMobileSidebar();
    initDropdowns();
    initModals();
});

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const match = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
    return match ? match[2] : '';
}

/**
 * Perform administrative POST action via fetch API
 */
async function superAdminAction(url, payload, confirmMessage = null) {
    if (confirmMessage) {
        if (window.EduNotify && typeof window.EduNotify.confirm === "function") {
            const ok = await window.EduNotify.confirm({
                title: "Confirm Action",
                message: confirmMessage,
                confirmText: "Continue",
                cancelText: "Cancel",
                variant: "warning"
            });
            if (!ok) return;
        } else {
            if (!confirm(confirmMessage)) return;
        }
    }

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.success) {
            showToast(data.message || "Action completed successfully.", "success");
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(data.error || "An error occurred during the operation.", "error");
        }
    } catch (error) {
        console.error("Super Admin Action Error:", error);
        showToast("Network error. Please try again.", "error");
    }
}

/**
 * Toast Notifications
 */
function showToast(message, type = "success") {
    let container = document.getElementById("superAdminToastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "superAdminToastContainer";
        container.className = "fixed bottom-5 right-5 z-50 flex flex-col gap-2";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    const bgColor = type === "success" ? "bg-emerald-600" : "bg-red-600";
    toast.className = `${bgColor} text-white px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 text-xs font-bold animate-fade-in`;
    const iconName = type === 'success' ? 'check_circle' : 'error';
    toast.innerHTML = `<span class="material-symbols-outlined !text-base">${iconName}</span><span class="toast-msg"></span>`;
    const msgEl = toast.querySelector('.toast-msg');
    if (msgEl) msgEl.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Mobile Sidebar Toggle
 */
function initMobileSidebar() {
    const toggleBtn = document.getElementById("mobileSidebarToggle");
    const sidebar = document.getElementById("superAdminSidebar");
    const backdrop = document.getElementById("sidebarBackdrop");

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("-translate-x-full");
            if (backdrop) backdrop.classList.toggle("hidden");
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", () => {
            sidebar.classList.add("-translate-x-full");
            backdrop.classList.add("hidden");
        });
    }
}

/**
 * Dropdown Menu Handlers
 */
function initDropdowns() {
    document.querySelectorAll("[data-dropdown-toggle]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const targetId = btn.getAttribute("data-dropdown-toggle");
            const menu = document.getElementById(targetId);
            if (menu) {
                document.querySelectorAll(".dropdown-menu").forEach(m => {
                    if (m !== menu) m.classList.add("hidden");
                });
                menu.classList.toggle("hidden");
            }
        });
    });

    document.addEventListener("click", () => {
        document.querySelectorAll(".dropdown-menu").forEach(m => m.classList.add("hidden"));
    });
}

/**
 * Modal Controls
 */
function initModals() {
    document.querySelectorAll("[data-modal-open]").forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-modal-open");
            const modal = document.getElementById(targetId);
            if (modal) modal.classList.remove("hidden");
        });
    });

    document.querySelectorAll("[data-modal-close]").forEach(btn => {
        btn.addEventListener("click", () => {
            const modal = btn.closest(".modal-backdrop");
            if (modal) modal.classList.add("hidden");
        });
    });
}
