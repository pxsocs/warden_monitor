$(document).ready(function () {
    quote = satoshi_refresh();
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
            quote = data['text'];
            phrases = splitString(300, quote);
            run_quote(phrases);
            $('#load_source').html(data['medium']);
            $('#load_date').html(data['date']);
            $('#subject').html(data['category']);
            $("#add_wisdom").show();
        },
        error: function (xhr, status, error) {
            console.log(status);
            console.log(error);
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            return (error)
        }
    });
};



