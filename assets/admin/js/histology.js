document.addEventListener('DOMContentLoaded', function() {
    // Get the orientation and side_sectioned_first elements
    const orientationField = document.getElementById('id_orientation');
    const sideSectionedFirstField = document.getElementById('id_side_sectioned_first');

    // Define the options for side_sectioned_first based on orientation
    const leftRightOptions = [
        {value: 'Left', text: 'Left'},
        {value: 'Right', text: 'Right'}
    ];

    const dorsalVentralOptions = [
        {value: 'Dorsal', text: 'Dorsal'},
        {value: 'Ventral', text: 'Ventral'}
    ];

    const anteriorPosteriorOptions = [
        {value: 'Anterior', text: 'Anterior'},
        {value: 'Posterior', text: 'Posterior'}
    ];

    // Function to update side_sectioned_first options
    function updateSideSectionedFirstOptions() {
        // Clear current options
        sideSectionedFirstField.innerHTML = '';

        // Get the current value of the orientation field
        const selectedOrientation = orientationField.value;

        let options = [];
        // Set options based on the selected orientation
        if (selectedOrientation === 'horizontal') {
            options = dorsalVentralOptions;
        } else if (selectedOrientation === 'coronal') {
            options = anteriorPosteriorOptions;
        } else if (selectedOrientation === 'sagittal' || selectedOrientation === 'oblique') {
            options = leftRightOptions;
        }

        // Add new options to the dropdown
        options.forEach(function(option) {
            const opt = document.createElement('option');
            opt.value = option.value;
            opt.text = option.text;
            sideSectionedFirstField.add(opt);
        });
    }

    // Listen for changes in the orientation field
    orientationField.addEventListener('change', updateSideSectionedFirstOptions);

    // Initialize the options on page load
    updateSideSectionedFirstOptions();
});
