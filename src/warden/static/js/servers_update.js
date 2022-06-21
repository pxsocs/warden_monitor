// Updates all servers and creates a table with results
var online = true;

$(document).ready(function () {
    update_price();
    update_servers();
    update_clock();
    update_max_height();
    update_block_details();

    $("#hidden-add-node").hide();
    $("#add_node").click(function () {
        $("#hidden-add-node").slideToggle("medium");
    });

    // New node being included
    $("#save_node").click(function () {

        node_name = $("#new_node_name").val();
        node_url = $("#new_node_url").val();
        is_private_node = document.getElementById("is_private_node");
        is_private_node = is_private_node.checked;
        send_message(`including node ${node_name}. please wait...`, 'info');
        data = {
            ["node_name"]: node_name,
            ["node_url"]: node_url,
            ["is_private_node"]: is_private_node
        }
        json_data = JSON.stringify(data)

        $.ajax({
            type: "POST",
            contentType: 'application/json',
            dataType: "json",
            data: json_data,
            url: "/node_action",
            success: function (data_back) {
                if (data_back == 'success') {
                    send_message(`Node ${node_name} added successfully. Please allow a few seconds before it shows in the list.`, 'success');
                } else {
                    send_message(`Node ${node_name} failed to be included.<br> Error: ${data_back}`, 'warning');
                }
                $("#hidden-add-node").slideToggle("medium");
            },
            error: function (xhr, status, error) {
                console.log(status);
                console.log(error);
                alerts_html = $('#alerts').html();
                send_message(`an error occured while adding node. message: ${status} | ${error}`, 'danger')
            }
        });


    });

    $("#wisdom_text").hide();
    $("#add_wisdom").hide();
    $("#add_wisdom").click(function () {
        $("#wisdom_text").slideToggle("medium");
    });
});



function update_block_details() {
    interval_block = 1000;
    const interval = setInterval(function () {
        target = '#block_info';
        url = '/get_pickle?filename=last_block_info&serialize=False';
        block_details = ajax_getter(url);
        url = '/get_pickle?filename=most_updated&serialize=False'
        most_updated_server = ajax_getter(url);

        currentTimeStamp = new Date(isoDateString).getTime()
        updated_time = new Date(updated_time).getTime()
        loaded_time = block_details['timestamp']
        loaded_time = loaded_time * 1000
        console.log(updated_time)
        console.log(loaded_time)
        time_difference = timeDifference(currentTimeStamp, loaded_time).toLowerCase();

        if (block_details == 'file not found') {
            $(target).html("<span class='text-warning'>offline</span>");
        } else {
            color = 'muted';
            icon = ''
            if (time_difference.includes('now')) {
                color = 'success',
                    icon = '<i class="fa-solid fa-cubes"></i>'
            } else if (time_difference.includes('seconds')) {
                color = 'success',
                    icon = '<i class="fa-solid fa-cubes"></i>'
            } else if (time_difference.includes('minutes')) {
                color = 'light'
                icon = '<i class="fa-solid fa-cube"></i>'
            } else if (time_difference.includes('hours')) {
                color = 'warning'
                icon = '<i class="fa-solid fa-clock"></i>'
            }
        }

        $(target).html(`<span class='text-${color}'>${icon}&nbsp;block found ${time_difference}</span>`);

    }, interval_block);
}


function update_clock() {
    interval_ms_clock = 5000;
    update_clock_content();
    const interval = setInterval(function () {
        update_clock_content();
    }, interval_ms_clock);
}

function update_clock_content() {
    target = '#clock_section';
    if (online == true) {
        var time = new Date();
        time_str = time.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
        $(target).text(time_str);
    } else {
        $(target).html("<span class='text-warning'>offline</span>");
    }
}

function update_max_height() {
    interval_ms_height = 1000;
    const interval = setInterval(function () {
        target = '#max_height';
        url = '/get_pickle?filename=max_tip_height&serialize=False';
        max_height = ajax_getter(url);
        if (max_height == 'file not found') {
            return
        } else {
            // Get current screen price
            current_height = parseFloat($(target).html().replace(',', ''));
            // If parser returns NaN (can happen if there's text) then set initial price to 0
            if (isNaN(current_height)) {
                current_height = 0;
            }
            // Grab latest price
            max_height = parseFloat(max_height);
            if (isNaN(max_height)) {
                $(target).html("<span class='text-muted'>" + $(target).text() + "</span>");
                return
            }
            $(target).animate_number({
                start_value: current_height,
                end_value: max_height,
                duration: 500,
                delimiter: ',',
                decimals: 0
            });
        }
    }, interval_ms_height);


}



function update_price() {
    interval_ms_price = 1000;
    const interval = setInterval(function () {
        target = '#price_section';
        url = '/get_pickle?filename=btc_price&serialize=False';
        latest_price = ajax_getter(url);
        if (latest_price == 'file not found') {
            $(target).html("loading...");
        } else {
            // Get current screen price
            initial_price = parseFloat($(target).html().replace(',', '').replace('$', ''));
            // If parser returns NaN (can happen if there's text) then set initial price to 0
            if (isNaN(initial_price)) {
                initial_price = 0;
            }
            // Grab latest price
            try {
                current_price = parseFloat(latest_price['price']);
            } catch (e) {
                current_price = NaN
            }
            if (isNaN(current_price)) {
                $(target).html("<span class='text-muted'>" + $(target).text() + "</span>");
                online = false
                return
            }

            // Check if price is current or outdated
            price_updated = new Date(latest_price['time'] + 'Z').toISOString()
            price_updated = new Date(price_updated).getTime();
            // Updated current time
            isoDateString = new Date().toISOString();
            currentTimeStamp = new Date(isoDateString).getTime()
            // Get a string of difference
            difference_numb = currentTimeStamp - price_updated;
            difference_str = timeDifference(currentTimeStamp, price_updated)
            minutes_ago = difference_numb / 1000 / 60
            if (minutes_ago >= 3) {
                $(target).html("<span class='text-muted'>" + (formatNumber(latest_price['price'], 2, "$ ")) + "</span>");
                $('#price_info').html("price feed delayed <br> last updated " + difference_str);
                return
            }

            online = true
            $('#price_info').html("");
            $(target).animate_number({
                start_value: initial_price,
                end_value: current_price,
                duration: 500,
                delimiter: ',',
                prepend: '$ ',

            });
        }
    }, interval_ms_price);


}

function createProgress(text, progress, bg = 'info', datainfo = undefined) {
    progress_txt = `<div class="progress">
                        <div class="progress-bar bg-${bg}"
                            data-toggle="tooltip"
                            data-placement="top"
                            title="${datainfo}"
                            role="progressbar"
                            style="width: ${progress}%; ">
                            ${text}
                        </div>
                    </div>`
    return (progress_txt);
}


function createPill(text, bg = 'info', datainfo = undefined) {
    // pill start
    pill = '<span class="badge  bg-' + bg + ' '
    if (datainfo != undefined) {
        pill += ' datainfo" data-toggle="tooltip" data-placement="top" title="' + datainfo + '"';
    }
    pill += '>' + text + '</span>&nbsp;';
    return (pill);
}


function update_servers() {
    // Updated every second
    interval_ms = 1000;
    const interval = setInterval(function () {
        // Get all servers
        url = '/node_action?full_node_data=true';
        server_data = ajax_getter(url);
        // Create table and parse data
        if ((server_data == 'file not found') || (server_data.length == 0)) {
            content_id = '#server_table';
            $(content_id).html(`
                <h6 class='text-center align-center text-warning'>
                <i class="fa-solid fa-triangle-exclamation fa-lg text-warning"></i>&nbsp;&nbsp;Servers not found</h6>
                `);
            return

        }
        // Sort the server_data by name
        server_data = sortObj(server_data, 'is_public');
        server_data = sortObj(server_data, 'name');
        create_table(server_data);
    }, interval_ms);
}

function create_table(data) {
    content_id = '#server_table';
    max_tip_height = 0;
    table = '<table class="table table-server">'
    // Create table header
    table += `
        <thead>
            <tr class='small-text'>
                <td>Source</td>
                <td></td>
                <td class="text-center">Latest Block</td>
                <td class="text-end">Updated</td>
                <td class="text-center"></td>
                <td class="text-end"></td>
                <td class="text-end"></td>
            </tr>
        </thead>
    `

    $.each(data, function (key_x, row) {
        // Start Row
        if (row.online == true) {
            table += "<tr class='box'>";
        } else {
            table += '<tr class="offlineBackground">';
        }

        // Source
        table += '<td class="text-start">' + row.name + '</td><td>';
        // Public or Private Node?
        if (row.is_public == true) {
            datainfo = "Public servers are a privacy risk. They have access to your IP address that can be linked to searches and activity. They are good for checking overall status but don't use for specific address and transaction searches. Use with caution."
            table += createPill('public node', 'dark', datainfo)
        } else {
            table += createPill('private node', 'dark', 'Running your own node provides a more private experience.')
        }
        table += '</td>';

        // Latest Block
        tip_height = row.tip_height
        // Save the max tip height for later
        max_tip_height = row.max_tip_height;
        progress = (tip_height / max_tip_height) * 100;
        if (isNaN(progress)) {
            bg = 'danger'
        }
        if (progress < 95) {
            bg = 'warning'
        }
        if (progress < 80) {
            bg = 'danger'
        }
        if (progress >= 95) {
            bg = 'success'
        }
        progress_bar = createProgress(formatNumber(progress, 0, '', '%'), progress, bg, 'Block height');

        table += `<td class="text-center small-text"> ${formatNumber(tip_height, 0)} / ${formatNumber(max_tip_height, 0)} ${progress_bar} </td>`;

        // Updated time
        isoDateString = new Date().toISOString();
        currentTimeStamp = new Date(isoDateString).getTime()
        // Mark current time as UTC with a Z
        updated_time = new Date(row.last_check + 'Z').toISOString()
        updated_time = new Date(updated_time).getTime()
        table += '<td class="text-end small-text">' + timeDifference(currentTimeStamp, updated_time) + '</td>';

        // Info & Pills
        table += '<td class="text-center">'


        // Onion Address, Local Host or Public Address
        if (row.onion == true) {
            table += createPill('Tor', 'success', 'This server is running on Tor')
        }
        if (row.localhost == true) {
            table += createPill('local network', 'success', 'This server is running inside your local network. It will not be accessible from the internet.')
        }

        // End Pills
        table += '</td>'


        // Check if online
        table += '<td class="text-center">'
        if (row.online == true) {
            table += createPill('ONLINE', 'success', 'server is online')
        } else {
            table += createPill('OFFLINE', 'danger', 'server is offline')
        }
        table += '</td>'

        // Add link to URL
        table += '<td class="text-end"><span class="badge bg-light">'
        table += '<a href="' + row.url + '" target="_blank"> <i class="fa-solid fa-arrow-up-right-from-square"></i></a>'
        table += '</span></td>'
        // Close Row
        table += '</tr>';
    });
    // Include hidden line for new node inclusion

    // Close Table
    table += '</table>';
    $(content_id).html(table);
}
