document.addEventListener("DOMContentLoaded", function () {
    const profilePage = document.getElementById("icdProfilePage");
    if (!profilePage) return;

    const apiUrl = profilePage.dataset.apiUrl;
    const baseImageApiUrl = profilePage.dataset.imageApiUrl;
    const csrfToken = profilePage.dataset.csrf;

    const form = document.getElementById("icdInstitutionForm");
    const btnSave = document.getElementById("btnSaveProfile");
    const saveSpinner = document.getElementById("saveSpinner");
    const saveIcon = document.getElementById("saveIcon");
    const toastEl = document.getElementById("statusToast");
    const toastMessage = document.getElementById("toastMessage");
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });

    function showToast(message, isError = false) {
        toastMessage.textContent = message;
        toastEl.className = `toast align-items-center text-bg-${isError ? 'danger' : 'success'} border-0`;
        toast.show();
    }

    // --- FORM SUBMISSION ---
    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });

        // UI Loading state
        btnSave.disabled = true;
        saveIcon.classList.add("d-none");
        saveSpinner.classList.remove("d-none");

        try {
            const response = await fetch(apiUrl, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify(data)
            });

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Server returned an invalid response (not JSON).");
            }

            const result = await response.json();
            
            if (result.success) {
                showToast("Institution profile updated successfully.");
                // Optionally reload to refresh the completion widget
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast(result.error || "Failed to update profile.", true);
            }
        } catch (error) {
            console.error("Profile save error:", error);
            showToast(error.message === "Server returned an invalid response (not JSON)." 
                ? "A server error occurred. Please try again." 
                : "Network error occurred.", true);
        } finally {
            btnSave.disabled = false;
            saveIcon.classList.remove("d-none");
            saveSpinner.classList.add("d-none");
        }
    });

    // --- IMAGE UPLOADS ---
    const btnEditLogo = document.getElementById("btnEditLogo");
    const btnEditBanner = document.getElementById("btnEditBanner");
    const logoInput = document.getElementById("imageUploadInput");
    const bannerInput = document.getElementById("bannerUploadInput");
    
    if (btnEditLogo) btnEditLogo.addEventListener("click", () => logoInput.click());
    if (btnEditBanner) btnEditBanner.addEventListener("click", () => bannerInput.click());

    async function handleImageUpload(inputEl, imageType) {
        const file = inputEl.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("image", file);

        // Construct correct URL by replacing 'placeholder' with actual type
        const uploadUrl = baseImageApiUrl.replace("placeholder", imageType);

        try {
            showToast(`Uploading ${imageType}...`);
            const response = await fetch(uploadUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            });

            const result = await response.json();
            if (result.success) {
                showToast(`${imageType.charAt(0).toUpperCase() + imageType.slice(1)} updated successfully.`);
                
                // Live preview update
                if (imageType === "logo") {
                    let imgEl = document.getElementById("logoPreviewImg");
                    if (imgEl.tagName !== 'IMG') {
                        // Create img if it was a placeholder div
                        const newImg = document.createElement("img");
                        newImg.id = "logoPreviewImg";
                        newImg.className = "icd-profile-avatar";
                        imgEl.parentNode.replaceChild(newImg, imgEl);
                        imgEl = newImg;
                    }
                    imgEl.src = result.url;
                } else if (imageType === "banner") {
                    const bannerEl = document.getElementById("bannerPreview");
                    bannerEl.style.backgroundImage = `url('${result.url}')`;
                }
                
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showToast(result.error || `Failed to upload ${imageType}.`, true);
            }
        } catch (error) {
            console.error(error);
            showToast(`Network error while uploading ${imageType}.`, true);
        }
    }

    if (logoInput) {
        logoInput.addEventListener("change", () => handleImageUpload(logoInput, "logo"));
    }
    
    if (bannerInput) {
        bannerInput.addEventListener("change", () => handleImageUpload(bannerInput, "banner"));
    }
});
