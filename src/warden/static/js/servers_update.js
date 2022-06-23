// Updates all servers and creates a table with results
var online = true;

const onion_icon = `
        <span data-bs-toggle="tooltip" data-bs-placement="top" title="Tor Node accessible with onion address">
        <i class="fa fa-tor-onion" aria-hidden="true"></i>
        </span>`

const local_icon = `
        <span data-bs-toggle="tooltip" data-bs-placement="top" title="Node accessible only at your local network">
        <i class="fa fa-home" aria-hidden="true"></i>
        </span>`

const online_icon = `<span data-bs-toggle="tooltip" data-bs-placement="top" title="node is online">
                        <i class="fa fa-signal text-success" aria-hidden="true"></i>
                    </span>`

const offline_icon = `<span data-bs-toggle="tooltip" data-bs-placement="top" title="node is offline and cannot be reached">
                        <i class="fa fa-signal text-danger" aria-hidden="true"></i>
                    </span>`

const private_icon = `<span data-bs-toggle="tooltip" data-bs-placement="top" title="this is a private node - the prefered method to check transactions and the bitcoin blockchain">
    <i class="fa fa-user-secret text-success" aria-hidden="true"></i>
    </span>`

const public_icon = `<span class="public_node" data-bs-toggle="tooltip" data-bs-placement="top" title="this is a public node - exercise caution when requesting private information like txs and bitcoin addresses - they may be linked to your IP address">
    <i class="fa fa-users text-muted" aria-hidden="true"></i>
    </span>`




$(document).ready(function () {

    initialize_tooltips();
    update_price();
    update_servers();
    update_clock();
    update_max_height();
    update_block_details();
    update_stats();

    $("#hidden-add-node").hide();
    $("#add_node").click(function () {
        $("#hidden-add-node").slideToggle("medium");
    });

    // New node being included
    $("#save_node").click(function () {
        add_edit_node();
    });

    $("#wisdom_text").hide();
    $("#add_wisdom").hide();
    $("#add_wisdom").click(function () {
        $("#wisdom_text").slideToggle("medium");
    });

});


function add_edit_node(action = undefined) {
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
    if (action != undefined) {
        data["action"] = action;
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
            } else if (data_back.includes('deleted')) {
                send_message(`Node ${node_name} deleted`, 'danger');
            } else {
                send_message(`Node ${node_name} failed to be included.<br> Error: ${data_back}`, 'muted');
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
};



function update_block_details() {
    interval_block = 1000;
    const interval = setInterval(function () {
        target = '#block_info';
        url = '/get_pickle?filename=last_block_info&serialize=False';
        block_details = ajax_getter(url);
        url = '/get_pickle?filename=most_updated&serialize=False'
        most_updated_server = ajax_getter(url);

        currentTimeStamp = new Date(isoDateString).getTime()
        try {
            updated_time = new Date(updated_time).getTime()
            loaded_time = block_details['timestamp']
            loaded_time = loaded_time * 1000
            time_difference = timeDifference(currentTimeStamp, loaded_time).toLowerCase();
        } catch {
            $(target).html("<span class='text-muted'>offline</span>");
            return
        }

        if (block_details == 'file not found') {
            $(target).html("<span class='text-muted'>offline</span>");
        } else {
            color = 'muted';
            icon = ''
            if (time_difference.includes('now')) {
                color = 'success',
                    icon = '<i class="fa fa-bell-ringing-o" aria-hidden="true"></i>'
            } else if (time_difference.includes('seconds')) {
                color = 'success',
                    icon = '<i class="fa fa-check-square" aria-hidden="true"></i>'
            } else if (time_difference.includes('minutes')) {
                color = 'light'
                icon = '<i class="fa fa-check-square" aria-hidden="true"></i>'
            } else if (time_difference.includes('hours')) {
                color = 'warning'
                icon = '<i class="fa fa-hourglass-half" aria-hidden="true"></i>'
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
            // Get current height at the screen
            current_height = parseFloat($(target).html().replace(',', ''));
            // If parser returns NaN (can happen if there's text) then set initial price to 0
            if (isNaN(current_height)) {
                current_height = 0;
            }
            // Grab latest height
            max_height = parseFloat(max_height);

            // Nothing returned, just send the text back and mute the text
            if (isNaN(max_height)) {
                $(target).html("<span class='text-muted'>" + $(target).text() + "</span>");
                return
            }

            // TICK TOCK NEXT BLOCK
            if (max_height == (current_height + 1)) {
                // Block height just increased. TICK TOCK NEXT BLOCK!
                console.log("Tick. Tock. Next Block.")
                $("#header_div").removeClass("bg-steel");
                $("#header_div").addClass("background-mover");
                $("#header_message").html("<span class='text-white text-bold'>new bitcoin block found</span>")
                    .delay(10000)
                    .fadeOut(function () {
                        $("#header_message").fadeOut('slow');
                        $("#header_div").addClass("bg-steel");
                        $("#header_div").removeClass("background-mover");
                    });

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


function update_stats() {
    interval_stats = 1000;
    const interval = setInterval(function () {
        target = '#stats';
        url = '/get_pickle?filename=nodes_status&serialize=False';
        stats = ajax_getter(url);
        if (typeof stats === 'string' || stats instanceof String) {
            stats = {
                'total_nodes': 'offline',
                'online': 'offline',
                'at_tip': 'offline',
                'onion': 'offline',
            }
        }
        if (stats == 'file not found') {
            return
        } else {
            html = `
            <div class="row">
            <div class="col">
                <div class="text-center">
                    <span class="dashboard-numbers"> ${stats['total_nodes']} </span><br/><hr>
                    <span class="clock"> total nodes </span>
                </div>
            </div>
            <div class="col">
                <div class="text-center">
                    <span class="dashboard-numbers"> ${stats['online']} </span><br/><hr>
                    <span class="clock"> online </span>
                </div>
            </div>
            <div class="col">
                <div class="text-center">
                    <span class="dashboard-numbers"> ${stats['at_tip']} </span><br/><hr>
                    <span class="clock"> at latest block </span>
                </div>
            </div>
            <div class="col">
                <div class="text-center">
                    <span class="dashboard-numbers"> ${stats['onion']} </span><br/><hr>
                    <span class="clock"> tor nodes </span>
                </div>
            </div>
            </div>
            `

            $(target).html(html);
        }
    }, interval_stats);


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
                current_price = parseInt(latest_price['price']);
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
                $(target).html("<span class='text-muted'>" + (formatNumber(latest_price['price'], 0, "$ ")) + "</span>");
                $('#price_info').html("price feed delayed <br> last updated " + difference_str);
                return
            }

            online = true
            $('#price_info').html('<span style="color: lightgreen;"><i class="fa fa-btc" aria-hidden="true"></i>&nbsp;NgU Tech</span>');
            $(target).animate_number({
                start_value: initial_price,
                end_value: current_price,
                duration: 500,
                decimals: 0,
                delimiter: ',',
                prepend: '$ ',

            });
        }
    }, interval_ms_price);


}

function createProgress(text, progress, bg = 'info', datainfo = undefined) {
    if (isNaN(progress)) {
        return '&nbsp;'
    } else {
        progress_txt = `<div class="progress">
                        <div class="progress-bar bg-${bg}"
                            data-bs-toggle="tooltip"
                            data-bs-placement="top"
                            title="${datainfo}"
                            role="progressbar"
                            style="width: ${progress}%; ">
                            ${text}
                        </div>
                    </div>`
        return (progress_txt);
    }
}


function createPill(text, bg = 'info', datainfo = undefined) {
    // pill start
    pill = '<span class="badge  bg-' + bg + ' '
    if (datainfo != undefined) {
        pill += ' datainfo" data-bs-toggle="tooltip" data-bs-placement="top" title="' + datainfo + '"';
    }
    pill += '>' + text + '</span>&nbsp;';
    return (pill);
}


function update_servers() {
    // Updated every second
    interval_ms = 5000;
    const interval = setInterval(function () {
        // Get all servers
        url = '/node_action?full_node_data=true';
        server_data = ajax_getter(url);
        // Create table and parse data
        if ((server_data == 'file not found') || (server_data.length == 0)) {
            content_id = '#server_table';
            $(content_id).html(`
                <h6 class='text-center align-center text-muted'>
                <i class="fa-solid fa-triangle-exclamation fa-lg text-muted"></i>&nbsp;&nbsp;Servers not found... please wait...</h6>
                `);
            return

        }
        // Sort the server_data by name
        server_data = sortObj(server_data, 'is_public');
        server_data = sortObj(server_data, 'name');
        create_table(server_data);
        initialize_tooltips();

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
                <td data-bs-toggle="tooltip" data-bs-placement="bottom" title="Click on name to edit">Node</td>
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
        table += "<tr class='box'>";

        // Do not update this html if currently being edited

        // Name
        table += '<td class="text-start datainfo" data-bs-toggle="tooltip" data-bs-placement="bottom" title="Click on name to edit"><span class="edit_name">' + row.name + '</span></td>';

        // Latest Block
        tip_height = row.tip_height
        // Save the max tip height for later
        max_tip_height = row.max_tip_height;
        progress = (tip_height / max_tip_height) * 100;
        if (isNaN(progress)) {
            bg = 'danger'
        }
        if (progress < 95) {
            bg = 'secondary'
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
        try {
            updated_time = new Date(row.last_check + 'Z').toISOString()
            updated_time = new Date(updated_time).getTime()
            table += '<td class="text-end small-text">' + timeDifference(currentTimeStamp, updated_time) + '</td>';
        } catch {
            table += '<td class="text-end small-text text-warning"> error checking. retrying...</td>';
        }

        // Info & Pills
        table += '<td class="text-center">'


        // Onion Address, Local Host or Public Address
        if (row.onion == true) {
            table += onion_icon
        }
        if (row.localhost == true) {
            table += local_icon
        }


        // Public or Private Node?
        if (row.is_public == true) {
            table += public_icon
        } else {
            table += private_icon
        }
        table += '</td>';


        // End Pills
        table += '</td>'


        // Check if online
        table += '<td class="text-center">'
        if (row.online == true) {
            table += online_icon
        } else {
            table += offline_icon
        }
        table += '</td>'

        // Add link to URL
        table += '<td class="text-end node_url">'
        table += '<a href="' + row.url + '" target="_blank" class="text-white"> <i class="fa fa-external-link" aria-hidden="true"></i></a>'
        table += '</td>'
        // Close Row
        table += '</tr>';
    });
    // Include hidden line for new node inclusion

    // Close Table
    table += '</table>';
    $(content_id).html(table);
    // Check if edit name is clicked, then change html
    $(".edit_name").click(function () {
        // Get node information from table
        node_name = $(this).text();
        node_url = $(this).parent().parent().find('.node_url').html()
        node_url = node_url.match(/href="([^"]*)/)[1];
        node_public = $(this).parent().parent().find('.public_node').html()
        if (node_public != undefined) {
            node_public = true
        } else {
            node_public = false
        }
        // Open new node edit and change values
        $("#hidden-add-node").show("medium");
        $("#new_node_name").val(node_name);
        $("#new_node_url").val(node_url);
        is_private_node = document.getElementById("is_private_node");
        is_private_node.checked = !node_public;
        // Change button text
        $("#new_node_txt").text("edit node");
        $("#save_node_txt").text("update");
        // Include Delete Button
        delete_button = `
            <button id="delete_node" class="btn btn-outline-danger btn-block">
            <i class="fa fa-trash-o" aria-hidden="true"></i>
            </button>`
        $("#delete_node_button").html(delete_button)
        $("#delete_node_button").click(function () {
            add_edit_node(action = 'delete')
        });

    });

}
