const previewImage = document.getElementById("preview");

const refreshPreview = () => {
    const url = `/api/screenshot?ts=${Date.now()}`;
    previewImage.src = url;
};

setInterval(refreshPreview, 350);
previewImage.addEventListener("error", () => setTimeout(refreshPreview, 500));
