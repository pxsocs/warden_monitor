$(document).ready(function () {
    satoshi_refresh();
    // Refresh if clicked
    $("#refresh_satoshi").click(function () {
        $('#refresh_satoshi').html('Please wait...');
        $('#refresh_satoshi').prop('disabled', true);
        satoshi_refresh();
    });
});

function satoshi_refresh() {
    $.ajax({
        type: 'GET',
        url: '/satoshi_quotes_json',
        dataType: 'json',
        success: function (data) {
            // Parse data
            // $('#loading').hide();
            // $('#quote_section').show();
            $('#quote_satoshi').html(data['text']);
            $('#load_source').html(data['medium']);
            $('#load_date').html(data['date']);
            $('#subject').html(data['category']);
            $("#add_wisdom").show();
            $('#refresh_satoshi').html('<i class="fa-solid fa-arrows-rotate"></i>&nbsp;refresh quote');
            $('#refresh_satoshi').prop('disabled', false);

        },
        error: function (xhr, status, error) {
            console.log(status);
            console.log(error);
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            $('#refresh_satoshi').html('Refresh Error. Try Again.');
            $('#refresh_satoshi').prop('disabled', false);
            return (error)

        }
    });
};



