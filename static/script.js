document.addEventListener('DOMContentLoaded', function() {
	var audio = (window.AudioContext || typeof webkitAudioContext !== 'undefined'),
		userlist = document.getElementById('userlist'),
		underlay = document.getElementById('underlay'),
		input = document.getElementById('input'),
		chat = document.getElementById('chat'),
		theme = (localStorage.theme && localStorage.theme.split(' ').length > 2) ? localStorage.theme : 'cozy night sans',
		waitTime = 1000,
		banned = false,
		users = {},
		muted = [],
		you = null,
		count = 0,
		lastMsg,
		lastRow,
		lastId,
		ws;

	// DOM-related functions

	var parser = function(raw_msg) {
		var profane_or_url = new RegExp(/(https?:\/\/[^< ]*[^<*.,?! :])|\b((?:t ?g+|fdp+|ba+t+a+r+d?|fiste?(?:u?r?)|ta+r+l+o+u+(z|s)e|taf+iol+e|péta+s+e?|put+(e|ain)|bi+t+e|cu+l|co+u+i+l+e|cha+t+e|chi+e+n+(?:a+s+)?e|sa+l+o+p+e?|(p ?d+)+|p(?:é|è|ai|ay)d(?:é|è|ai|ay)|salaud|sc?hne+c?k|(?:em)?me+r+d+(?:i?er?|eu(?:x|r))|bo+r+de+l+|fo+u+t+r+e|ni+qu?(?:é|eu?r?)|encu+l+(?:é+|eu?r)|enf+oiré+|branl+eu?r?|fi+o+t+e|bu+r+n+e|co+n(?:ne|n?a+rd|n?a+s+e)?)s?)\b/, 'gi'),
			rules = [
			/*{
				test: msg => msg.includes('http'),
				run: msg => msg.replace(/https?:\/\/[^< ]*[^<*.,?! :]/g, '<a href="$&" target="_blank">$&</a>')
			},*/
			{
				test: msg => msg.match(profane_or_url),
				run: msg => msg.replace(profane_or_url, function(matched) { return matched.includes('http')? `<a href="${matched}" target="_blank">${matched}</a>` : '<span class="pinktext">' + '♥'.repeat(matched.length) + '</span>'; })
			},
			{
				test: msg => msg.includes('**'),
				run: msg => msg.replace(/\*{2}([^\*]+)\*{2}?/g, '<span class="spoiler">$1</span>')
			},
			{
				test: msg => msg.includes('://vocaroo.com/i/'),
				run: msg => msg.replace(/<a href="https?:\/\/vocaroo.com\/i\/(\w+)" target="_blank">https?:\/\/vocaroo.com\/i\/\w+<\/a>/g, '<audio controls><source src="https://vocaroo.com/media_command.php?media=$1&command=download_mp3" type="audio/mpeg"><source src="https://vocaroo.com/media_command.php?media=$1&command=download_webm" type="audio/webm"></audio>$&')
			},
			{
				test: msg => msg.startsWith('&gt;'),
				run: msg => msg.replace(/(.+)/g, '<span class="greentext">$1</span>')
			}
		];

		var tests = rules.filter(rule => ('test' in rule) && rule.test(raw_msg));
		return tests.filter(rule => 'run' in rule).reduce((prev, rule) => rule.run(prev), raw_msg);
	};

	var addLine = function(pkmn, txt, datemsg, rowclass, uid) {
		var atBottom = (chat.scrollTop === (chat.scrollHeight - chat.offsetHeight)),
			text = document.createElement('div'),
			uid = uid || null;
		text.innerHTML = txt;

		if(lastId !== uid) {
			var row = document.createElement('div'),
				msg = document.createElement('div');

			if(pkmn.name === 'info') {
				var i = document.createElement('i');
				i.className = 'material-icons';
				i.appendChild(document.createTextNode('info_outline'));
				row.appendChild(i);
			}
			else {
				var pic = document.createElement('div'),
					img1 = document.createElement('img'),
					img2 = document.createElement('img'),
					img3 = document.createElement('img');

				img1.src = '/pokemon/' + pkmn.img + '.gif';
				img2.src = '/img/pokemon/' + pkmn.img + '.gif';
				img3.src = '/dev/pokemon/' + pkmn.img + '.png';
				pic.appendChild(img1);
				pic.appendChild(img2);
				pic.appendChild(img3);
				row.appendChild(pic);

				var name = document.createElement('div');
				name.appendChild(document.createTextNode(pkmn.name + ' ' + pkmn.adjective));
				name.style.color = pkmn.color;
				msg.appendChild(name);

			}

			if(pkmn.color) {
				row.style.borderColor = pkmn.color;
				row.style.color = pkmn.color;
			}

			row.className = rowclass;
			row.appendChild(msg);
			lastRow = msg;

			var dt = document.createElement('div');
			dt.appendChild(document.createTextNode((new Date(datemsg)).toLocaleTimeString('fr-FR')));
			row.appendChild(dt);

			chat.appendChild(row);

			if(!document.hasFocus())
				document.title = '(' + ++count + ') Loult.family';
		}

		lastRow.appendChild(text);
		lastId = uid;

		if(atBottom)
			chat.scrollTop = chat.scrollHeight;
	};

	var addUser = function(userid, params, profile) {
		if(userid in users)
			return;

		users[userid] = params;

		if(ambtn.checked && muted.indexOf(userid) === -1)
			muted.push(userid);

		var row = document.createElement('li');
		row.appendChild(document.createTextNode(params.name));
		row.style.color = params.color;
		row.style.backgroundImage = 'url("/pokemon/' + params.img + '.gif")';

		if(!params.you) {
			var i = document.createElement('i');
			i.className = 'material-icons';
			i.appendChild(document.createTextNode('volume_' + (muted.indexOf(userid) != -1 ? 'off' : 'up')));
			row.appendChild(i);

			i.onmousedown = function() {
				if(muted.indexOf(userid) != -1) {
					muted.splice(muted.indexOf(userid), 1);
					i.innerHTML = 'volume_up';
				}
				else {
					muted.push(userid);
					i.innerHTML = 'volume_off';
				}
			};
		}
		else {
			underlay.style.backgroundImage = 'url("/dev/pokemon/' + params.img + '.png")';
			you = userid;
		}

		var phead = document.createElement('div'),
			pbody = document.createElement('div'),
			pdiv = document.createElement('div'),
			idiv = document.createElement('div'),
			pimg = document.createElement('img'),
			l = document.createElement('i');
		l.className = 'material-icons';
		l.appendChild(document.createTextNode('my_location'));

		pimg.src = '/img/pokemon/' + params.img + '.gif';
		idiv.appendChild(pimg);

		phead.style.backgroundImage = 'linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0) 35px, rgba(' + parseInt(params.color.slice(1, 3), 16) + ', ' + parseInt(params.color.slice(3, 5), 16) + ', ' + parseInt(params.color.slice(5, 7), 16) + ', 0.2) 35px, ' + params.color + ' 100%)';
		phead.appendChild(idiv);
		phead.appendChild(document.createElement('br'));
		phead.appendChild(document.createTextNode(params.name + ' ' + params.adjective));

		pbody.appendChild(l);
		pbody.appendChild(document.createTextNode(profile.city + ' (' + profile.departement + ')'));
		pbody.appendChild(document.createElement('br'));
		pbody.appendChild(document.createTextNode(profile.age + ' ans'));
		pbody.appendChild(document.createElement('br'));
		pbody.appendChild(document.createTextNode(profile.orientation));
		pbody.appendChild(document.createElement('br'));
		pbody.appendChild(document.createTextNode(profile.job));

		pdiv.appendChild(phead);
		pdiv.appendChild(pbody);
		row.appendChild(pdiv);

		userlist.appendChild(row);
		users[userid].dom = row;
	};

	var delUser = function(userid) {
		userlist.removeChild(users[userid].dom);
		delete users[userid];
	};


	// Limit the number of messages displayed

	var limitHistory = function () {

		var history = document.getElementById('history');
		var limit = history.value;

		if (limit == 'full' || typeof limit == 'undefined') {
			return;
		}

		// var limit = 20;
		var hcount = 0;
		var history = chat.children;
		
		// increments counter for each messages, just one time for other type of blocks
		for (var i = 0; i < history.length; i++) {
			var cnode = history.item(i);
			if(cnode.classList.contains('msg') || cnode.classList.contains('backlog')) {
				for(var j = 2; j <= (cnode.childNodes[1].childElementCount); j++) {
					hcount++;
				}
			}
			else {
				hcount++;
			}	
		}

		// removes only the oldest message if block contains several ones
		if(hcount > limit) {
			var node = history.item(0);
			if(node.classList.contains('msg')) {
				// tightly coupled with current html structure
				var cnode = node.childNodes[1];
				if(typeof cnode.childNodes[2] !== 'undefined') {
					cnode.childNodes[1].remove();
				}
				else 
					node.remove();
			}
			else { 
				node.remove();
			}
		}
	};

	var historycfg = { attributes: false, childList: true, subtree: true };
	var historyObserver = new MutationObserver(limitHistory);
	historyObserver.observe(chat, historycfg);


	// Focus-related functions

	var dontFocus = false;

	var refocus = function(evt) {
		if(!dontFocus && !window.getSelection().toString())
			input.focus();
	};

	document.body.addEventListener('mouseup', refocus, false);

	window.addEventListener('resize', function(evt) {
		chat.scrollTop = chat.scrollHeight;
		refocus();
	});

	window.onfocus = function() {
		 if(count > 0) {
			document.title = 'Loult.family';
			count = 0;
		}
		refocus();
	};

	// Preferences

	var gear = document.getElementById('gear'),
		overlay = document.getElementById('overlay'),
		cover = document.getElementById('cover'),
		close = document.getElementById('close'),
		ambtn = document.getElementById('am'),
		head = document.getElementById('head'),
		main = document.getElementById('main'),
		foot = document.getElementById('foot'),
		themes = document.getElementById('theme'),
		colors = document.getElementById('color'),
		fonts = document.getElementById('font'),
		settings = theme.split(' ');

	var openWindow = function() {
		dontFocus = true;
		input.blur();
		overlay.style.display = 'block';
		head.className = main.className = foot.className = 'blur-in';
	};

	var closeWindow = function() {
		dontFocus = false;
		refocus();
		overlay.style.display = 'none';
		head.className = main.className = foot.className = '';
	};

	gear.onclick = openWindow;
	cover.onclick = close.onclick = closeWindow;

	var applyTheme = function() {
		theme = localStorage.theme = settings.join(' ');
		document.body.className = theme.replace('_', ' ');
		chat.scrollTop = chat.scrollHeight;
	};

	applyTheme();
	themes.value = settings[0];
	colors.value = settings[1];
	fonts.value = settings[2];

	themes.onchange = function() {
		settings[0] = this.value;
		applyTheme();
	};

	colors.onchange = function() {
		settings[1] = this.value;
		applyTheme();
	};

	fonts.onchange = function() {
		settings[2] = this.value;
		applyTheme();
	};

	// Languages

	var select = document.getElementById('lang'),
		lang = document.cookie.match(/lang=(\w{2})/);

	if(!lang) {
		var ln = navigator.language.substr(0, 2);
		switch(ln) {
			case 'fr':
			case 'es':
			case 'de':
				lang = ln;
			break;
			default:
				lang = 'en';
		}
		document.cookie = 'lang=' + lang + '; Path=/';
	}
	else
		lang = lang[1];

	select.value = lang;

	select.onchange = function() {
		lang = this.value;
		document.cookie = 'lang=' + lang + '; Path=/';
	};

	// Sound and volume

	if(audio) {
		var vol = document.getElementById('vol'),
			volrange = document.getElementById('volrange'),
			context = new (window.AudioContext || webkitAudioContext)(),
			volume = (context.createGain ? context.createGain() : context.createGainNode());
		volume.connect(context.destination);

		var changeVolume = function() {
			localStorage.volume = volume.gain.value = volrange.value * 0.01;
			changeIcon(volrange.value);
		};

		var changeIcon = function(v) {
			vol.innerHTML = (v > 0 ? (v > 50 ? 'volume_up' : 'volume_down') : 'volume_mute');
		};

		if(localStorage.volume) {
			volrange.value = localStorage.volume * 100;
			volume.gain.value = localStorage.volume;
			changeIcon(volrange.value);
		}

		vol.onclick = function() {
			volume.gain.value = (volume.gain.value > 0 ? 0 : volrange.value * 0.01);
			changeIcon(volume.gain.value * 100);
		};

		volrange.oninput = changeVolume;
	}

	// Speech

	if('webkitSpeechRecognition' in window) {
		var mic = document.getElementById('mic'),
			recognition = new webkitSpeechRecognition(),
			recognizing = false;

		mic.innerHTML = 'mic_none';

		mic.onclick = function () {
			if(recognizing) {
				recognition.stop();
				mic.innerHTML = 'mic_none';
				return;
			}
			mic.innerHTML = 'mic';
			recognition.lang = lang + '-' + ((lang === 'en') ? 'US' : lang.toUpperCase());
			recognition.start();
			input.value = '';
		};

		recognition.continuous = true;
		recognition.interimResults = true;

		recognition.onstart = function() {
			recognizing = true;
		};

		recognition.onerror = function(event) {
			// console.log(event.error);
		};

		recognition.onend = function() {
			recognizing = false;
		};

		recognition.onresult = function(event) {
			var interim_transcript = '';
			for(var i = event.resultIndex; i < event.results.length; i++)
				if(event.results[i].isFinal) {
					var m = input.value.trim();
					if(m.length) {
						ws.send(JSON.stringify({type: 'msg', msg: m, lang: lang}));
						lastMsg = input.value;
						input.value = '';
					}
				}
				else
					interim_transcript += event.results[i][0].transcript;

			input.value = interim_transcript.trim();
			input.value = input.value.charAt(0).toUpperCase() + input.value.slice(1);
		};
	}

	// Users list display

	var userswitch = document.getElementById('userswitch');

	userswitch.onclick = function() {
		var atBottom = (chat.scrollTop === (chat.scrollHeight - chat.offsetHeight));
		userlist.style.width = (userlist.style.width === '0px' ? '200px' : '0px');
		head.style.paddingRight = underlay.style.right = userlist.style.width;
		if(atBottom)
			chat.scrollTop = chat.scrollHeight;
	};

	// WebSocket-related functions

	var wsConnect = function() {
		ws = new WebSocket(location.origin.replace('http', 'ws') + '/socket' + location.pathname);
		// ws = new WebSocket('wss://loult.family/socket/' + location.pathname);
		ws.binaryType = 'arraybuffer';

		var lastMuted = false;

		input.onfocus = function(evt) {
			if (audio && context && context.state !== "running") {
				context.resume().then(() => {
				    console.log('Playback resumed successfully');
				  });
			}
		}

		input.onkeydown = function(evt) {
			underlay.className = '';
			if(evt.keyCode === 13 && input.value) {
				var trimed = input.value.trim();
				if(trimed.charAt(0) === '/') {
					if(trimed.match(/^\/at(?:k|q|ta(?:ck|que))\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ type : 'attack', target : splitted[1], order : ((splitted.length === 3) ? parseInt(splitted[2]) : 0) }));
					}
					else if(trimed.match(/^\/(?:en|es|fr|de)\s/i)) {
						ws.send(JSON.stringify({type: 'msg', msg: trimed.substr(4), lang: trimed.substr(1, 2).toLowerCase()}));
						underlay.className = 'pulse';
					}
					else if(trimed.match(/^\/((?:list)+)$/i)) {
						ws.send(JSON.stringify({type: 'list'}));
						underlay.className = 'pulse';
					}
					else if(trimed.match(/^\/((?:inv)+)$/i)) {
						ws.send(JSON.stringify({type: 'inventory'}));
					}
					else if(trimed.match(/^\/give\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ type : 'give', object_id: parseInt(splitted[1]), target : splitted[2], order : ((splitted.length === 4) ? parseInt(splitted[3]) : 0) }));
					}
					else if(trimed.match(/^\/use\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ type : 'use', object_id: parseInt(splitted[1]), params : splitted.slice(2) }));
					}
					else if(trimed.match(/^\/take\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ type : 'take', object_id: parseInt(splitted[1])}));
					}
					else if(trimed.match(/^\/trash\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ type : 'trash', object_id: parseInt(splitted[1])}));
					}
					else if(trimed.match(/^\/vol(?:ume)?\s(?:\d+)$/i) && audio) {
						volrange.value = Math.min(100, trimed.match(/\d+$/i)[0]);
						changeVolume();
					}

					else if(trimed.match(/^\/(?:help|aide)$/i)) {
						var d = new Date;
						addLine({name : 'info'}, '/attaque, /attack, /atq, /atk : Lancer une attaque sur quelqu\'un. Exemple : /attaque Miaouss 2', d, 'part', 'help');
						addLine({name : 'info'}, '/en, /es, /fr, /de : Envoyer un message dans une autre langue. Exemple : /en Where is Pete Ravi?', d, 'part', 'help');
						if(audio)
							addLine({name : 'info'}, '/volume, /vol : Régler le volume rapidement. Exemple : /volume 50', d, 'part', 'help');
						addLine({name : 'info'}, '/me : Réaliser une action. Exemple: /me essaie la commande /me.', d, 'part', 'help');
						addLine({name : 'info'}, '/use : Utiliser un object de son inventaire. Exemple: /use 3 Miaouss 2', d, 'part', 'help');
						addLine({name : 'info'}, '/give : Donner un objet de son inventaire à quelqu\'un d\'autre. Exemple: /give 2 Tauros', d, 'part', 'help');
						addLine({name : 'info'}, '/inv : Afficher son inventaire.', d, 'part', 'help');
						addLine({name : 'info'}, '/list : Afficher l\inventaire public du salon', d, 'part', 'help');
						addLine({name : 'info'}, '/trash : Jeter un objet de son inventaire. Exemple: /trash 3', d, 'part', 'help');
						addLine({name : 'info'}, '/take : Prendre un object dans l\'inventaire public du salon. Exemple: /take 4', d, 'part', 'help');
						addLine({name : 'info'}, '> : Indique une citation. Exemple : >Je ne reviendrais plus ici !', d, 'part', 'help');
						addLine({name : 'info'}, '** ** : Masquer une partie d\'un message. Exemple : Carapuce est un **chic type** !', d, 'part', 'help');
					}
					else if(trimed.match(/^\/me\s/i))
						ws.send(JSON.stringify({type: 'me', msg: trimed.substr(4)}));
					else if(trimed.match(/^\/(?:poker|flip|omg|drukqs)$/i)) {
						document.body.className = theme.replace('_', ' ') + ' ' + trimed.substr(1);
						chat.scrollTop = chat.scrollHeight;
					}
					else if(trimed.match(/^\/((?:bisw)+)$/i)) {
						document.body.className = 'cozy pink comic';
						chat.scrollTop = chat.scrollHeight;
					}
					else {
						ws.send(JSON.stringify({type: 'msg', msg: trimed, lang: lang}));
						underlay.className = 'pulse';
					}
				}
				else if(trimed.length) {
					ws.send(JSON.stringify({type: 'msg', msg: trimed, lang: lang}));
					underlay.className = 'pulse';
				}

				lastMsg = input.value;
				input.value = '';
			}
			else if(evt.keyCode === 38 || evt.keyCode === 40) {
				evt.preventDefault();
				input.value = (lastMsg && !input.value ? lastMsg : '');
			}
		};

		ws.onopen = function() {
			waitTime = 1000;
		};

		ws.onmessage = function(msg) {
			if(typeof msg.data === 'string') {
				msg = JSON.parse(msg.data);
				lastMuted = (muted.indexOf(msg.userid) != -1);

				switch(msg.type) {
					case 'msg':
					case 'bot':
						if(!lastMuted)
							addLine(users[msg.userid], parser(msg.msg), msg.date, msg.type, msg.userid);
					break;

					case 'me':
						if(!lastMuted)
							addLine({name : 'info', color : users[msg.userid].color}, 'Le ' + users[msg.userid].name + ' ' + users[msg.userid].adjective + ' ' + parser(msg.msg), msg.date, 'me', msg.userid);
					break;

					case 'connect':
						addUser(msg.userid, msg.params, msg.profile);
						if(!lastMuted)
							addLine({name : 'info'}, 'Un ' + msg.params.name + ' ' + msg.params.adjective + ' apparaît !', msg.date, 'log', msg.type);
					break;

					case 'disconnect':
						if(!lastMuted)
							addLine({name : 'info'}, 'Le ' + users[msg.userid].name + ' ' + users[msg.userid].adjective + ' s\'enfuit !', msg.date, 'part', msg.type);
						delUser(msg.userid);
					break;

					case 'attack':
						switch(msg['event']) {
							case 'attack':
								addLine({name : 'info'}, users[msg.attacker_id].name + ' attaque ' + users[msg.defender_id].name + ' !', msg.date, 'log', msg.type);
							break;

							case 'dice':
								addLine({name : 'info'}, users[msg.attacker_id].name + ' tire un ' + msg.attacker_dice + ' + ('+ msg.attacker_bonus + '), ' + users[msg.defender_id].name + ' tire un ' + msg.defender_dice + ' + (' + msg.defender_bonus + ') !', msg.date, 'log', msg.type);
							break;

							case 'effect':
								addLine({name : 'info'}, users[msg.target_id].name + ' est maintenant affecté par l\'effet ' + msg.effect + ' !', msg.date, 'log', msg.type);
								if(msg.target_id === you) {
									var d = new Date(msg.date);
									d.setSeconds(d.getSeconds() + msg.timeout);
									setTimeout(function() { addLine({name : 'info'}, 'L\'effet ' + msg.effect + ' est terminé.', d, 'part', 'expire'); }, msg.timeout * 1000);
								}
							break;

							case 'invalid':
								addLine({name : 'info'}, 'Impossible d\'attaquer pour le moment, ou pokémon invalide', (new Date), 'kick', 'invalid');
							break;

							case 'nothing':
								addLine({name : 'info'}, 'Il ne se passe rien...', msg.date, 'log', msg.type);
							break;
						}
					break;

					case 'antiflood':
						switch(msg['event']) {
							case 'banned':
								addLine({name : 'info'}, 'Le ' + users[msg.flooder_id].name + ' ' + users[msg.flooder_id].adjective + ' était trop faible. Il est libre maintenant.', msg.date, 'kick', msg.type);
							break;

							case 'flood_warning':
								addLine({name : 'info'}, 'Attention, la qualité de vos contributions semble en baisse. Prenez une grande inspiration.', msg.date, 'kick', msg.type);
							break;
						}
					break;

					case 'wait':
						addLine({name : 'info'}, 'La connection est en cours. Concentrez-vous quelques instants avant de dire des âneries.', msg.date, 'log', msg.type);
					break;

					case 'notification':
                        addLine({name : 'info'}, msg.msg,("date" in msg) ? msg.date : (new Date), 'info');
                    break;

					case 'userlist':
					    // flushing previous user list just in case
					    for(var i in users)
				            delUser(i);

						for(var i = 0; i < msg.users.length; i++)
							addUser(msg.users[i].userid, msg.users[i].params, msg.users[i].profile);
					break;

					case 'backlog':
						for(var i = 0; i < msg.msgs.length; i++)
							if(msg.msgs[i].type === 'me')
								addLine({name : 'info', color : msg.msgs[i].user.color}, 'Le ' + msg.msgs[i].user.name + ' ' + msg.msgs[i].user.adjective + ' ' + parser(msg.msgs[i].msg), msg.msgs[i].date, 'backlog me', msg.msgs[i].userid);
							else
								addLine(msg.msgs[i].user, parser(msg.msgs[i].msg), msg.msgs[i].date, 'backlog ' + msg.msgs[i].type, msg.msgs[i].userid);

						addLine({name : 'info'}, 'Vous êtes connecté.', (new Date), 'log', 'connected');
					break;

					case 'banned':
						banned = true;
						ws.close();
					break;

					// conditions dedicated to objects
					case 'give':
					    switch(msg['response']){
					        case 'invalid_target':
					            addLine({name : 'info'}, 'Utilisateur récepteur inexistant', (new Date), 'kick', 'invalid');
					        break;

					        case 'exchanged':
					            addLine({name : 'info'}, users[msg.sender].name + ' donne ' + msg.obj_name + ' à  ' + users[msg.receiver].name + ".", msg.date, 'log');
					        break;
					    }
					break;

					case 'object':
					    switch(msg['response']){
					        case 'invalid_id':
					            addLine({name : 'info'}, 'Indice d\'objet dans l\'inventaire inexistant', (new Date), 'log', 'invalid');
					        break;

					        case 'object_trashed':
					            addLine({name : 'info'}, 'L\'objet ' + msg.object_name + ' a été jeté.', (new Date), 'log');
					        break;

					        case 'object_taken':
					            addLine({name : 'info'}, 'L\'objet ' + msg.object_name + ' a pris dans l\'inventaire commun.', (new Date), 'log');
					        break;
					    }
					break;
				}
			}
			else if(!lastMuted && audio && volume.gain.value > 0) {
				context.decodeAudioData(msg.data, function(buf) {
					var source = context.createBufferSource();
					source.buffer = buf;
					source.connect(volume);
					source.start();
				});
			}
		};

		ws.onerror = function(e) {
			console.log(['error', e]);
		};

		ws.onclose = function() {
			for(var i in users)
				delUser(i);

			if(banned)
				for(var i = 0; i < 500; i++)
					addLine({name : 'info'}, 'CIVILISE TOI.', (new Date), 'kick');
			else {
				addLine({name : 'info'}, 'Vous êtes déconnecté.', (new Date), 'part');
				addLine({name : 'info'}, 'Nouvelle connexion en cours...', (new Date), 'part');
				waitTime = Math.min(waitTime * 2, 120000);
				window.setTimeout(wsConnect, waitTime);
			}
		};
	};

	wsConnect();

});
