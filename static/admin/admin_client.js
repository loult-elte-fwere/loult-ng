document.addEventListener('DOMContentLoaded', function() {
    message_display = document.getElementById('message');
    ws = new WebSocket(location.origin.replace('http', 'ws') + '/socket' + location.pathname);
    
    for (var i = 0; i < document.forms.length; i++) {
	let form = document.forms[i];
	let userid = form.elements.namedItem('userid').value;
	let channel = form.elements.namedItem('channel').value;
	let action = form.elements.namedItem("action").options;
	let ban_duration = form.elements.namedItem('ban_duration').options;
	//let ban_duration = form.elements.namedItem("ban_duration").options;
	form.addEventListener('submit', function(event) {
	    event.preventDefault();
	    let msg = { "mod" : "ipban",
			"userid" : userid,
			"channel" : channel,
			"action" : action[action.selectedIndex].value,
		        "duration" : ban_duration[ban_duration.selectedIndex].value
		      };
	    ws.send(JSON.stringify(msg));
	    message_display.style.display = "block";
	    message_display.innerHTML = "Action effectuée.";
	    location.reload();
	});
    }
});
