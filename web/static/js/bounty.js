document.addEventListener('DOMContentLoaded', function() {
    // Handle claim bounty form submission
    const claimForm = document.querySelector('form[action*="claim_bounty"]');
    if (claimForm) {
        claimForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(claimForm);

            fetch(claimForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert('Bounty claimed successfully!');
                    window.location.reload();
                } else {
                    alert('Failed to claim bounty: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while claiming the bounty.');
            });
        });
    }
});