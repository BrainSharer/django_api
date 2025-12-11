document.addEventListener("DOMContentLoaded", function () {
  console.log('xxxxxxxxxxxxxxxx tif inline.js loaded');
    document.querySelectorAll(".toggle-status").forEach(function (button) {
        button.addEventListener("click", function () {
            const id = this.dataset.id;
            fetch(`toggle-status/${id}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload just the changelist table
                    // location.reload();
                    alert('Status toggled successfully. Please refresh the page to see the updated status.');
                }
            });
        });
    });
});

// helper to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}