// Updates all servers and creates a table with results

$(document).ready(function () {
    update_servers();

    $("#hidden-add-node").hide();
    $("#add_node").click(function () {
        $("#hidden-add-node").slideToggle("medium");
    });

    $("#wisdom_text").hide();
    $("#add_wisdom").click(function () {
        $("#wisdom_text").slideToggle("medium");
    });
});

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
        url = '/get_pickle?filename=mps_server_status&serialize=False';
        server_data = ajax_getter(url);
        // Create table and parse data
        if (server_data == 'file not found') {
            content_id = '#server_table';
            $(content_id).html(`
                <h6>
                <i class="fa-solid fa-triangle-exclamation fa-lg text-warning"></i>&nbsp;&nbsp;No servers found. Check your connections.</h6>
                `);

        }
        // Sort the server_data by name
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
                <td class="text-end"></td>
            </tr>
        </thead>
    `

    $.each(data, function (key_x, row) {
        // Start Row
        if (row.online == true) {
            table += '<tr>';
        } else {
            table += '<tr class="offlineBackground">';
        }

        // Source
        table += '<td class="text-start">' + row.name + '</td><td>';
        // Public or Private Node?
        if (row.public == true) {
            datainfo = "Public servers are a privacy risk. They have access to your IP address that can be linked to searches and activity. They are good for checking overall status but don't use for specific address and transaction searches. Use with caution."
            table += createPill('public node', 'dark', datainfo)
        } else {
            table += createPill('private node', 'dark', 'Running your own node provides a more private experience.')
        }
        table += '</td>';

        // Latest Block
        tip_height = row.tip_height
        // Save the max tip height for later
        max_tip_height = Math.max(max_tip_height, tip_height);
        table += '<td class="text-center">' + formatNumber(tip_height, 0) + '</td>';

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

        // Check if Fully Synched
        table += '<td class="text-center">'
        if (row.synched == true) {
            table += createPill('100%', 'success', 'server is synchronized and at the latest block')
        } else {
            table += createPill('unsynced', 'danger', 'server is not synchronized up to the latest block')
        }
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
