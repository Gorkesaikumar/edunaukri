document.addEventListener('DOMContentLoaded', function() {
    const btnReviewJob = document.getElementById('btnReviewJob');
    const mainForm = document.getElementById('vacancyForm');
    const previewModal = new bootstrap.Modal(document.getElementById('previewModal'));
    const btnPublish = document.getElementById('btnPublishJob');
    const actionInput = document.getElementById('formAction');

    if (!btnReviewJob || !mainForm) return;

    btnReviewJob.addEventListener('click', function() {
        // 1. Validate Form
        if (!mainForm.checkValidity()) {
            mainForm.reportValidity();
            return;
        }

        // 2. Extract Data
        const title = document.getElementById('vacTitle').value.trim();
        const dept = document.getElementById('vacDept').value.trim();
        const empSelect = document.getElementById('vacEmployment');
        const employment = (empSelect && empSelect.selectedIndex >= 0) ? empSelect.options[empSelect.selectedIndex].text : '';
        
        const workSelect = document.getElementById('vacWorkType');
        const workType = (workSelect && workSelect.selectedIndex >= 0) ? workSelect.options[workSelect.selectedIndex].text : '';
        const city = document.getElementById('vacCity') ? document.getElementById('vacCity').value.trim() : '';
        const desc = document.getElementById('vacDesc') ? document.getElementById('vacDesc').value.trim() : '';
        const req = document.getElementById('vacReq') ? document.getElementById('vacReq').value.trim() : '';
        const expMin = document.getElementById('vacExpMin') ? document.getElementById('vacExpMin').value : '';
        const expMax = document.getElementById('vacExpMax') ? document.getElementById('vacExpMax').value : '';
        const salMin = document.getElementById('vacSalMin') ? document.getElementById('vacSalMin').value : '';
        const salMax = document.getElementById('vacSalMax') ? document.getElementById('vacSalMax').value : '';

        // 3. Hydrate Modal
        document.getElementById('previewTitle').textContent = title || 'Job Title';
        document.getElementById('previewLocation').textContent = city ? city : 'Location not specified';
        
        // Tags
        const tagsContainer = document.getElementById('previewTags');
        tagsContainer.innerHTML = '';
        if (dept) tagsContainer.innerHTML += `<span class="fjd-tag">${dept}</span>`;
        if (employment) tagsContainer.innerHTML += `<span class="fjd-tag">${employment}</span>`;
        if (workType) tagsContainer.innerHTML += `<span class="fjd-tag">${workType}</span>`;

        // Salary Format
        if (salMin || salMax) {
            let salText = "";
            if (salMin && salMax) salText = `₹${salMin} - ${salMax} LPA`;
            else if (salMin) salText = `From ₹${salMin} LPA`;
            else if (salMax) salText = `Up to ₹${salMax} LPA`;
            tagsContainer.innerHTML += `<span class="fjd-tag">${salText}</span>`;
        }

        // Meta Rows
        const metaDl = document.getElementById('previewMeta');
        metaDl.innerHTML = '';
        if (expMin || expMax) {
            let expText = "";
            if (expMin && expMax) expText = `${expMin}–${expMax} years`;
            else if (expMin) expText = `${expMin}+ years`;
            else if (expMax) expText = `Up to ${expMax} years`;
            
            metaDl.innerHTML += `
            <div class="fjd-profile-dl__row">
                <dt>Experience</dt>
                <dd>${expText}</dd>
            </div>`;
        }

        // Description
        const descBlock = document.getElementById('previewDescBlock');
        const descContent = document.getElementById('previewDescContent');
        if (desc) {
            descBlock.style.display = 'block';
            descContent.innerHTML = desc.replace(/\n/g, '<br>');
        } else {
            descBlock.style.display = 'none';
        }

        // Requirements
        const reqBlock = document.getElementById('previewReqBlock');
        const reqContent = document.getElementById('previewReqContent');
        if (req) {
            reqBlock.style.display = 'block';
            reqContent.innerHTML = req.replace(/\n/g, '<br>');
        } else {
            reqBlock.style.display = 'none';
        }

        // Show Modal
        previewModal.show();
    });

    btnPublish.addEventListener('click', function() {
        // Change action to publish if needed, though we removed save draft so it's always publish
        if (actionInput) actionInput.value = 'publish';
        
        // Disable button to prevent double submit
        btnPublish.disabled = true;
        btnPublish.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Publishing...';
        
        mainForm.submit();
    });
});
