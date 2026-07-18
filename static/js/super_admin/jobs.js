/**
 * Super Admin Jobs and Vacancies Management
 * Handles modals, AJAX data fetching, and interactions.
 */

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function openJobDetailModal(jobId, jobType) {
    const modal = new bootstrap.Modal(document.getElementById('jobDetailModal'));
    modal.show();
    
    // Set loading state
    document.getElementById('jobDetailModalLabel').textContent = 'Loading...';
    document.getElementById('jdm-company-name').textContent = '...';
    document.getElementById('jdm-description').innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div> Loading details...';
    
    // Fetch data
    const url = jobType === 'faculty' 
        ? `/api/v1/admin/vacancies/${jobId}/` 
        : `/api/v1/admin/jobs/${jobId}/`;

    fetch(url)
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                populateJobDetailModal(res.data, jobType);
            } else {
                window.showToast('Error loading job details: ' + (res.error || 'Unknown error'), true);
            }
        })
        .catch(err => {
            console.error(err);
            window.showToast('Network error occurred while fetching job details.', true);
        });
}

function populateJobDetailModal(data, jobType) {
    const title = data.title || 'Untitled';
    document.getElementById('jobDetailModalLabel').textContent = title;
    
    const isFaculty = jobType === 'faculty';
    const org = isFaculty ? data.college : data.company;
    const orgName = org ? org.name : 'Unknown Organization';
    const loc = data.location || (data.locations && data.locations.length > 0 ? data.locations[0].city : 'Remote/Hybrid');
    
    document.getElementById('jdm-company-name').innerHTML = `<strong>${escapeHtml(orgName)}</strong> &bull; ${escapeHtml(loc)}`;
    
    // Logo
    const logoContainer = document.getElementById('jdm-company-logo');
    if (org && org.logo_url) {
        logoContainer.innerHTML = `<img src="${escapeHtml(org.logo_url)}" class="img-fluid" alt="${escapeHtml(orgName)}">`;
    } else {
        logoContainer.innerHTML = `<i class="fas fa-${isFaculty ? 'university' : 'building'} text-muted"></i>`;
    }
    
    document.getElementById('jdm-domain').textContent = isFaculty ? 'Faculty Domain' : 'IT Domain';
    document.getElementById('jdm-domain').className = `badge mb-2 ${isFaculty ? 'bg-warning text-dark' : 'bg-primary-subtle text-primary'}`;
    
    document.getElementById('jdm-description').textContent = data.description || 'No description provided.';
    document.getElementById('jdm-responsibilities').textContent = data.roles_responsibilities || 'N/A';
    document.getElementById('jdm-requirements').textContent = data.requirements || 'N/A';
    
    // Skills
    const skillsContainer = document.getElementById('jdm-skills');
    skillsContainer.innerHTML = '';
    const skills = data.required_skill_names || [];
    if (skills.length > 0) {
        skills.forEach(skill => {
            const span = document.createElement('span');
            span.className = 'badge bg-light text-secondary border';
            span.textContent = skill;
            skillsContainer.appendChild(span);
        });
    } else {
        skillsContainer.innerHTML = '<span class="text-muted small">No specific skills listed.</span>';
    }
    
    // At a glance
    document.getElementById('jdm-employment').textContent = data.employment_type || 'N/A';
    
    let salary = 'Not Disclosed';
    if (data.salary_min || data.salary_max) {
        const curr = data.salary_currency || 'INR';
        salary = `${curr} ${data.salary_min || 0} - ${data.salary_max || 0}`;
    }
    document.getElementById('jdm-salary').textContent = salary;
    
    let exp = 'Not Specified';
    if (data.experience_min !== null || data.experience_max !== null) {
        exp = `${data.experience_min || 0} - ${data.experience_max || 0} Years`;
    }
    document.getElementById('jdm-experience').textContent = exp;
    document.getElementById('jdm-vacancies').textContent = data.vacancies || 1;
    
    // Statistics
    document.getElementById('jdm-views').textContent = data.view_count || 0;
    document.getElementById('jdm-applications').textContent = data.application_count || 0;
    
    const appsBtn = document.getElementById('jdm-view-apps-btn');
    appsBtn.onclick = () => openApplicationsModal(data.id, jobType, title);
    
    // Recruiter
    const recruiter = data.posted_by;
    if (recruiter) {
        const name = `${recruiter.first_name} ${recruiter.last_name}`;
        document.getElementById('jdm-recruiter-name').textContent = name;
        document.getElementById('jdm-recruiter-initial').textContent = name.charAt(0).toUpperCase();
        document.getElementById('jdm-recruiter-contact').textContent = `${recruiter.email} ${recruiter.phone_number ? ' | ' + recruiter.phone_number : ''}`;
        document.getElementById('jdm-recruiter-verified').innerHTML = recruiter.is_verified 
            ? '<i class="fas fa-check-circle text-success" title="Verified"></i>' 
            : '<i class="fas fa-exclamation-circle text-warning" title="Unverified"></i>';
    } else {
        document.getElementById('jdm-recruiter-name').textContent = 'Unknown Recruiter';
        document.getElementById('jdm-recruiter-contact').textContent = '-';
        document.getElementById('jdm-recruiter-verified').innerHTML = '';
        document.getElementById('jdm-recruiter-initial').textContent = '?';
    }
    
    // Action Buttons
    const actionsContainer = document.getElementById('jdm-action-buttons');
    actionsContainer.innerHTML = '';
    
    if (data.status === 'pending_approval' || data.status === 'draft') {
        const approveBtn = document.createElement('button');
        approveBtn.className = 'btn btn-success';
        approveBtn.innerHTML = '<i class="fas fa-check me-1"></i> Approve';
        approveBtn.onclick = () => confirmModerationAction(data.id, jobType, 'approve', 'Approve Job Posting', 'Are you sure you want to approve and publish this job posting?');
        actionsContainer.appendChild(approveBtn);
    }
    
    if (data.status !== 'rejected' && data.status !== 'closed') {
        const rejectBtn = document.createElement('button');
        rejectBtn.className = 'btn btn-danger';
        rejectBtn.innerHTML = '<i class="fas fa-times me-1"></i> Reject';
        rejectBtn.onclick = () => confirmModerationAction(data.id, jobType, 'reject', 'Reject Job Posting', 'Please provide remarks for rejecting this posting. It will be hidden from the marketplace.');
        actionsContainer.appendChild(rejectBtn);
    }
}

function openApplicationsModal(jobId, jobType, jobTitle) {
    // Hide job detail modal if open
    const detailModalEl = document.getElementById('jobDetailModal');
    if (detailModalEl && detailModalEl.classList.contains('show')) {
        bootstrap.Modal.getInstance(detailModalEl).hide();
    }
    
    const modal = new bootstrap.Modal(document.getElementById('applicationListModal'));
    modal.show();
    
    document.getElementById('alm-job-title').textContent = jobTitle || 'Job Applications';
    document.getElementById('alm-loader').classList.remove('d-none');
    document.getElementById('alm-table-body').innerHTML = '';
    document.getElementById('alm-empty-state').classList.add('d-none');
    
    // Fetch apps
    const url = jobType === 'faculty' 
        ? `/api/v1/admin/applications/faculty/?vacancy_id=${jobId}` 
        : `/api/v1/admin/applications/jobs/?job_posting_id=${jobId}`;

    fetch(url)
        .then(res => res.json())
        .then(res => {
            document.getElementById('alm-loader').classList.add('d-none');
            if (res.success && res.data && res.data.results) {
                renderApplications(res.data.results, jobType);
            } else {
                document.getElementById('alm-empty-state').classList.remove('d-none');
            }
        })
        .catch(err => {
            console.error(err);
            document.getElementById('alm-loader').classList.add('d-none');
            document.getElementById('alm-empty-state').classList.remove('d-none');
            window.showToast('Network error occurred while fetching applications.', true);
        });
}

function renderApplications(apps, jobType) {
    const tbody = document.getElementById('alm-table-body');
    tbody.innerHTML = '';
    document.getElementById('alm-count').textContent = apps.length;
    
    if (apps.length === 0) {
        document.getElementById('alm-empty-state').classList.remove('d-none');
        return;
    }
    
    window._currentAppsList = apps;
    apps.forEach((app, idx) => {
        const tr = document.createElement('tr');
        
        const applicant = app.applicant_details || {};
        const name = applicant.first_name ? `${applicant.first_name} ${applicant.last_name}` : (app.applicant_name_snapshot || 'Unknown Applicant');
        const email = applicant.email || 'No email';
        const phone = applicant.phone_number || '-';
        const exp = applicant.experience !== undefined ? `${applicant.experience} yrs` : 'Unknown';
        const avatar = applicant.avatar_url ? `<img src="${escapeHtml(applicant.avatar_url)}" class="rounded-circle" width="36" height="36">` : `<div class="bg-secondary text-white rounded-circle d-flex align-items-center justify-content-center" style="width:36px; height:36px;">${escapeHtml(name.charAt(0).toUpperCase())}</div>`;
        const appliedDate = new Date(app.applied_at).toLocaleDateString();
        
        let statusBadgeClass = 'bg-secondary';
        if (app.status === 'SHORTLISTED') statusBadgeClass = 'bg-info';
        if (app.status === 'INTERVIEW') statusBadgeClass = 'bg-warning text-dark';
        if (app.status === 'OFFERED' || app.status === 'HIRED') statusBadgeClass = 'bg-success';
        if (app.status === 'REJECTED') statusBadgeClass = 'bg-danger';

        tr.innerHTML = `
            <td class="ps-4">
                <div class="d-flex align-items-center gap-3">
                    ${avatar}
                    <div>
                        <div class="fw-bold text-dark">${escapeHtml(name)}</div>
                        <div class="small text-muted">${escapeHtml(applicant.designation || '-')}</div>
                    </div>
                </div>
            </td>
            <td>
                <div class="small"><i class="fas fa-envelope text-muted me-1"></i> ${escapeHtml(email)}</div>
                <div class="small"><i class="fas fa-phone text-muted me-1"></i> ${escapeHtml(phone)}</div>
            </td>
            <td>${escapeHtml(exp)}</td>
            <td>${escapeHtml(appliedDate)}</td>
            <td><span class="badge ${statusBadgeClass}">${escapeHtml(app.status)}</span></td>
            <td class="text-end pe-4">
                <button class="btn btn-sm btn-light border text-primary me-1" onclick="viewCandidateProfile(window._currentAppsList[${idx}])"><i class="fas fa-user"></i> Profile</button>
                <button class="btn btn-sm btn-light border text-danger" onclick="viewResume(window._currentAppsList[${idx}].resume_url || '', window._currentAppsList[${idx}].applicant_name_snapshot || '')"><i class="fas fa-file-pdf"></i> Resume</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function viewCandidateProfile(appData) {
    const modal = new bootstrap.Modal(document.getElementById('candidateProfileModal'));
    modal.show();
    
    const applicant = appData.applicant_details || {};
    const name = applicant.first_name ? `${applicant.first_name} ${applicant.last_name}` : (appData.applicant_name_snapshot || 'Unknown Applicant');
    
    document.getElementById('cpm-name').textContent = name;
    document.getElementById('cpm-designation').textContent = applicant.designation || (applicant.company ? `At ${applicant.company}` : 'No Designation');
    document.getElementById('cpm-location').innerHTML = `<i class="fas fa-map-marker-alt me-1"></i> ${escapeHtml(applicant.location || 'Location Not Specified')}`;
    document.getElementById('cpm-experience').innerHTML = `<i class="fas fa-briefcase me-1"></i> ${escapeHtml(applicant.experience !== undefined ? applicant.experience + ' Years' : 'Unknown')}`;
    
    document.getElementById('cpm-email').textContent = applicant.email || 'No email';
    document.getElementById('cpm-phone').textContent = applicant.phone_number || 'No phone';
    document.getElementById('cpm-status').textContent = appData.status;
    document.getElementById('cpm-applied-date').textContent = new Date(appData.applied_at).toLocaleString();
    
    document.getElementById('cpm-cover-letter').textContent = appData.cover_letter || 'No cover letter provided.';
    
    // Resume tab
    document.getElementById('cpm-resume-name').textContent = `${name.replace(' ', '_')}_Resume.pdf`;
    document.getElementById('cpm-resume-date').textContent = new Date(appData.applied_at).toLocaleDateString();
    
    document.getElementById('cpm-view-resume-btn').onclick = () => viewResume(appData.resume_url, name);
}

function viewResume(url, candidateName) {
    if (!url || url === 'undefined') {
        window.showToast('Resume not found or not uploaded by the candidate.', true);
        return;
    }
    const modal = new bootstrap.Modal(document.getElementById('resumeViewerModal'));
    modal.show();
    
    document.getElementById('rvm-candidate-name').textContent = candidateName || 'Candidate';
    document.getElementById('rvm-loader').classList.remove('d-none');
    document.getElementById('rvm-iframe').classList.add('d-none');
    
    const iframe = document.getElementById('rvm-iframe');
    iframe.src = url;
    
    iframe.onload = () => {
        document.getElementById('rvm-loader').classList.add('d-none');
        iframe.classList.remove('d-none');
    };
    
    document.getElementById('rvm-download').href = url;
}

let pendingAction = null;
function confirmModerationAction(jobId, jobType, action, title, message) {
    pendingAction = { jobId, jobType, action };
    
    document.getElementById('mam-title').textContent = title;
    document.getElementById('mam-message').textContent = message;
    document.getElementById('mam-remarks').value = '';
    
    let iconHtml = '';
    if (action === 'approve') iconHtml = '<i class="fas fa-check-circle text-success" style="font-size:3rem;"></i>';
    else if (action === 'reject') iconHtml = '<i class="fas fa-times-circle text-danger" style="font-size:3rem;"></i>';
    else if (action === 'close' || action === 'archive') iconHtml = '<i class="fas fa-exclamation-triangle text-warning" style="font-size:3rem;"></i>';
    
    document.getElementById('mam-icon').innerHTML = iconHtml;
    
    const modal = new bootstrap.Modal(document.getElementById('moderationActionModal'));
    modal.show();
}

document.getElementById('mam-confirm-btn').addEventListener('click', () => {
    if (!pendingAction) return;
    
    const remarks = document.getElementById('mam-remarks').value;
    const url = pendingAction.jobType === 'faculty'
        ? `/api/v1/admin/vacancies/${pendingAction.jobId}/${pendingAction.action}/`
        : `/api/v1/admin/jobs/${pendingAction.jobId}/${pendingAction.action}/`;
        
    const btn = document.getElementById('mam-confirm-btn');
    const ogText = btn.textContent;
    btn.textContent = 'Processing...';
    btn.disabled = true;

    // Use meta tag or form input if HttpOnly cookie is enabled, fallback to cookie.
    const csrftoken = document.querySelector('meta[name="csrf-token"]')?.content ||
        document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
        document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ remarks: remarks })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            bootstrap.Modal.getInstance(document.getElementById('moderationActionModal')).hide();
            // Try to hide detail modal if open
            const detailModalEl = document.getElementById('jobDetailModal');
            if (detailModalEl && detailModalEl.classList.contains('show')) {
                bootstrap.Modal.getInstance(detailModalEl).hide();
            }
            window.showToast('Action completed successfully.', false);
            window.location.reload();
        } else {
            window.showToast('Failed: ' + (res.error || 'Unknown error'), true);
        }
    })
    .catch(err => {
        console.error(err);
        window.showToast('Network error occurred.', true);
    })
    .finally(() => {
        btn.textContent = ogText;
        btn.disabled = false;
        pendingAction = null;
    });
});

// Override the old superAdminAction if it exists so we use our modals
window.superAdminAction = function(url, data, confirmMessage) {
    // If it's a direct url like action API, extract action from data
    if (data && data.action) {
        confirmModerationAction(url.split('/').slice(-2)[0], data.type, data.action, 'Confirm Action', confirmMessage);
    } else {
        window.showToast(confirmMessage, false);
    }
}
