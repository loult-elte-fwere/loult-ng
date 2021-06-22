document.addEventListener('DOMContentLoaded', function () {
        var audio = (window.AudioContext || typeof webkitAudioContext !== 'undefined'),
            audio_sources = {},
            userlist = document.getElementById('userlist'),
            underlay = document.getElementById('underlay'),
            input = document.getElementById('input'),
            chat = document.getElementById('chat'),
            chest = document.getElementById('chest'),
            inventory_display = document.getElementById('inventory_display'),
            bank_display = document.getElementById('bank_display'),
            theme = (localStorage.theme && localStorage.theme.split(' ').length > 2) ? localStorage.theme : 'bibw night sans medium',
            waitTime = 1000,
            banned = false,
            users = {},
            muted = JSON.parse(localStorage.getItem('mutedUsers')) ? JSON.parse(localStorage.getItem('mutedUsers')) : [],
            unmuted = JSON.parse(localStorage.getItem('unmutedUsers')) ? JSON.parse(localStorage.getItem('unmutedUsers')) : [],
            embed = localStorage.getItem('embed') ? localStorage.getItem('embed') : [],
            you = null,
            count = 0,
            lastMsg,
            lastRow,
            lastId,
            lastType = null,
            inventory = "",
            item_list = "",
            menuOpen = false,
            dragged_item,
            uploadItemBlob,
            ws;

        inventory_display.innerHTML = "<span>...</span>";
        bank_display.innerHTML = "<span>...</span>";

        // DOM-related functions

        var parser = function (raw_msg) {
            let rules = [
                {
                    test: msg => msg.includes('http'),
                    run: msg => msg.replace(/https?:\/\/[^< ]*[^<*.,?! :]/g, '<a href="$&" target="_blank">$&</a>')
                },
                {
                    test: msg => msg.includes('://old.vocaroo.com/i/'),
                    run: msg => msg.replace(/<a href="https?:\/\/old.vocaroo.com\/i\/(\w+)" target="_blank">https?:\/\/old.vocaroo.com\/i\/\w+<\/a>/g, '<audio controls><source src="https://old.vocaroo.com/media_command.php?media=$1&command=download_mp3" type="audio/mpeg"><source src="https://old.vocaroo.com/media_command.php?media=$1&command=download_webm" type="audio/webm"></audio>$&')
                },
                {
                    test: msg => (msg.includes('://vocaroo.com/') || msg.includes('://voca.ro/')),
                    run: msg => msg.replace(/<a href="https?:\/\/(?:vocaroo.com|voca.ro)\/(\w+)" target="_blank">https?:\/\/(?:vocaroo.com|voca.ro)\/\w+<\/a>/g, '<audio controls><source src="https://media.vocaroo.com/mp3/$1" type="audio/mpeg"></source></audio>$&')
                },
                {
                    test: msg => msg.includes('https://bnl.loult.family/media/content/audio/'),
                    run: msg => msg.replace(/<a href="(https:\/\/bnl.loult.family\/media\/content\/audio\/[a-z0-9]+)" target="_blank">.*<\/a>/g, '<audio controls><source src="$1" ></source></audio>$&')
                },
                {
                    test: msg => msg.includes('**'),
                    run: msg => msg.replace(/\*{2}([^\*]+)\*{2}?/g, '<span class="spoiler">$1</span>')
                },
                {
                    test: msg => msg.startsWith('&gt;'),
                    run: msg => msg.replace(/(.+)/g, '<span class="greentext">$1</span>')
                }
            ];

            var tests = rules.filter(rule => ('test' in rule) && rule.test(raw_msg));
            return tests.filter(rule => 'run' in rule).reduce((prev, rule) => rule.run(prev), raw_msg);
        };
        var autoscroll = function () {
            //auto scroll page down, if scroll bar at the bottom
            if (Math.floor(chat.scrollTop) + chat.offsetHeight >= (chat.scrollHeight - chat.offsetHeight)) {
                chat.scrollTop = chat.scrollHeight + 500;
            }
        }
        var addEmbedYtb = function (ytbId) {

            //create iframe at the bottom of last Div
            let ifrm = document.createElement('iframe');
            ifrm.src = 'https://www.youtube.com/embed/' + ytbId;
            ifrm.frameborder = 0;
            lastRow.appendChild(ifrm);
            autoscroll();
        }
        var addImgEmbed = function (imgURL) {

            //create IMG at the bottom of last Div
            let imgDiv = document.createElement('img');
            imgDiv.onload = autoscroll;
            imgDiv.src = imgURL;
            lastRow.appendChild(imgDiv);
        }
        var addLine = function (pkmn, txt, datemsg, rowclass, uid) {
            var atBottom = (chat.scrollTop >= (chat.scrollHeight - chat.offsetHeight) - 50),
                text = document.createElement('div'),
                uid = uid || null;
            text.innerHTML = txt;

            if (lastId !== uid || lastType !== rowclass) {
                var row = document.createElement('div'),
                    msg = document.createElement('div');

                if (pkmn.name === 'info') {
                    var i = document.createElement('i');
                    i.appendChild(document.createTextNode('info_outline'));
                    i.innerHTML = '<img class="pokeball" src="img/icons/pokeball.svg"/>';
                    row.id
                    row.appendChild(i);
                } else if (pkmn.name === 'bank') {
                    var i = document.createElement('i');
                    i.appendChild(document.createTextNode('info_outline'));
                    i.innerHTML = '<img class="pokeball" src="img/icons/coffre.svg"/>';
                    row.appendChild(i);
                } else {
                    var pic = document.createElement('div'),
                        img1 = document.createElement('img'),
                        img2 = document.createElement('img'),
                        img3 = document.createElement('img');
                    img4 = document.createElement('img');

                    img1.src = '/img/pokemon/small/' + pkmn.img + '.gif';
                    img2.src = '/img/pokemon/medium/' + pkmn.img + '.gif';
                    img3.src = '/img/pokemon/big/' + pkmn.img + '.png';
                    img4.src = '/img/pokemon/mini/' + pkmn.img + '.png';
                    pic.appendChild(img1);
                    pic.appendChild(img2);
                    pic.appendChild(img3);
                    pic.appendChild(img4);
                    row.appendChild(pic);

                    var name = document.createElement('div');
                    name.appendChild(document.createTextNode(pkmn.name + ' ' + pkmn.adjective));
                    name.style.color = pkmn.color;
                    msg.appendChild(name);

                }

                if (pkmn.color) {
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

                if (!document.hasFocus())
                    document.title = '(' + ++count + ') Loult.family';
            }

            lastRow.appendChild(text);
            lastId = uid;
            lastType = rowclass;

            if (atBottom)
                chat.scrollTop = chat.scrollHeight;
        };

        var addUser = function (userid, params, profile) {
            if (userid in users)
                return;

            users[userid] = params;
            //check if same pokemon and add orderId
            let orderId = 0;

            for (let a in users) {
                if (users[a].name === params.name) orderId++;
            }
            users[userid].orderId = orderId;

            localStorage.setItem('mutedUsers', JSON.stringify(muted));
            localStorage.setItem('unmutedUsers', JSON.stringify(unmuted));

            /* first connection, page refreshed, or any cases where a user can
               be in neither of both *muted list */
            if (muted.indexOf(userid) === -1 && unmuted.indexOf(userid) === -1) {
                if (ambtn.checked && !params.you)
                    muted.push(userid);
                else
                    unmuted.push(userid);
            }

            var row = document.createElement('li');
            row.setAttribute('title', params.name + ' ' + params.adjective);
            //var newSpan = document.createElement('span');

            // items can be dragged on users to use
            row.setAttribute("data-id", users[userid].name + " " + users[userid].orderId);
            row.addEventListener("dragstart", item_dragstart);
            row.addEventListener("dragover", item_dragover);
            row.addEventListener("dragenter", item_dragenter);
            row.addEventListener("drop", item_drop);

            // newSpan.appendChild(document.createTextNode(params.name));
            row.appendChild(document.createTextNode(params.name));

            // row.appendChild ( newSpan );
            row.style.color = params.color;
            row.style.backgroundImage = 'url("/img/pokemon/small/' + params.img + '.gif")';

            if (!params.you) {

                // Muted button
                var i = document.createElement('i');

                i.className = 'material-icons';
                i.appendChild(document.createTextNode('volume_' + (
                    unmuted.indexOf(userid) === -1 ? 'off' : 'up')));
                row.appendChild(i);
                muted_button = row.getElementsByClassName('material-icons')[0];
                muted_button.onmousedown = function (e) {
                    e.stopPropagation();

                    if (muted.indexOf(userid) !== -1) {
                        muted.splice(muted.indexOf(userid), 1);
                        unmuted.push(userid);
                        i.innerHTML = 'volume_up';
                    } else {
                        unmuted.splice(unmuted.indexOf(userid), 1);
                        muted.push(userid);
                        i.innerHTML = 'volume_off';

                        // stop all sounds coming from user *now*
                        if (audio && audio_sources[userid] !== undefined) {
                            audio_sources[userid].forEach(function (value, index) {
                                value.stop();
                            });
                            audio_sources[userid] = [];
                        }
                    }
                    localStorage.setItem('mutedUsers', JSON.stringify(muted));
                    localStorage.setItem('unmutedUsers', JSON.stringify(unmuted));
                };
            } else {
                underlay.style.backgroundImage = 'url("/img/pokemon/big/' + params.img + '.png")';
                you = userid;
            }

            // Attack button
            var i2 = document.createElement('img');
            i2.className = 'sword';
            i2.src = 'img/icons/sword.svg';
            row.appendChild(i2);
            row.onmousedown = function () {
                ws.send(JSON.stringify({type: 'attack', target: params.name, order: orderId}));
            };

            var phead = document.createElement('div'),
                pbody = document.createElement('div'),
                pdiv = document.createElement('div'),
                idiv = document.createElement('div'),
                pimg = document.createElement('img'),
                l = document.createElement('i');
            l.className = 'material-icons';
            l.appendChild(document.createTextNode('my_location'));

            pimg.src = '/img/pokemon/medium/' + params.img + '.gif';
            idiv.appendChild(pimg);

            phead.style.backgroundImage = 'linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0) 35px, rgba(' + parseInt(params.color.slice(1, 3), 16) + ', ' + parseInt(params.color.slice(3, 5), 16) + ', ' + parseInt(params.color.slice(5, 7), 16) + ', 0.2) 35px, ' + params.color + ' 100%)';
            phead.style.backgroundColor = '#222';
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
//	row.appendChild(pdiv);

<<<<<<< HEAD
		userlist.appendChild(row);
		users[userid].dom = row;
	};

	var delUser = function(userid) {
		userlist.removeChild(users[userid].dom);
		delete users[userid];
	};

	hist = document.getElementById('history'),
		hist.value = localStorage.getItem('history') ? localStorage.getItem('history') : 'full';

	hist.onchange = function() {
		localStorage.history = hist.value;
	}

	// Limit the number of messages displayed
	var limitHistory = function () {
		var limit = localStorage.getItem('history');

		if (limit == 'full' || typeof limit === 'undefined' || !limit) {
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

	var refocus = function(event) {
		if(!dontFocus && !window.getSelection().toString() && !menuOpen)
			input.focus();
	};

	// clicking anywhere on the chat and userlist refocuses to the text input area
	document.body.getElementsByTagName("main")[0].addEventListener('mouseup', refocus, false);

	window.addEventListener('resize', function(evt) {
		chat.scrollTop = chat.scrollHeight;
		refocus();
	});

	window.onfocus = function(event) {
		if(count > 0) {
			document.title = 'Loult.family';
			count = 0;
		}
		refocus();
	};

	// Preferences
	var gear = document.getElementById('gear'),
		embedbtn = document.getElementById('embed'),
		ambtn = document.getElementById('am'),
		head = document.getElementById('head'),
		main = document.getElementById('main'),
		foot = document.getElementById('foot'),
		themes = document.getElementById('theme'),
		poketype = document.getElementById('poketype'),
		colors = document.getElementById('color'),
		fonts = document.getElementById('font'),
		settings = theme.split(' ');

	ambtn.checked = localStorage.getItem('automute') == 'true' ? true : false;
	embedbtn.checked = localStorage.getItem('embed') == 'true' ? true : false;

	ambtn.onchange = function() {
		localStorage.setItem('automute', ambtn.checked);
	}

	embedbtn.onchange = function() {
		localStorage.setItem('embed', embedbtn.checked);
	}


	var applyTheme = function() {
		theme = localStorage.theme = settings.join(' ');
		document.body.className = theme.replace('_', ' ');
		chat.scrollTop = chat.scrollHeight;
	};

	applyTheme();
	themes.value = settings[0];
	colors.value = settings[1];
	fonts.value = settings[2];
	poketype.value = settings[3];

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

	poketype.onchange = function () {
		settings[3] = this.value;
		applyTheme();
	};


	// Languages

	var select = document.getElementById('lang'),
		lang = localStorage.lang;

	if(!lang) {
		var ln = navigator.language.substr(0, 2);
		switch(ln) {
			case 'fr':
			case 'es':
			case 'de':
				lang = ln;
				break;
			default:
				lang = 'fr';
		}
		localStorage.lang = lang;
	}

	select.value = lang;

	select.onchange = function() {
		lang = this.value;
		localStorage.lang = lang
	};

	// cookie setting in the menu

	var cookieInput = document.getElementById("cookie"),
		cookieSetButton = document.getElementById("change-cookie");

	var updateCookieDisplay = function () {
		try {
			cookieInput.value = document.cookie.match(/id=(.*?);/)[1];
		} catch (e) {
			console.log("Invalid cookie format. Stick to 'id=yourcookie'")
		}

	}
	if (document.cookie) {
		updateCookieDisplay()
	}

	cookieSetButton.onclick = function () {
		document.cookie = 'id=' + cookieInput.value + '; Path=/';
		ws.close();
	}


	// Sound and volume

	if(audio) {
		var vol = document.getElementById('vol'),
			volrange = document.getElementById('volrange'),
			context = new (window.AudioContext || webkitAudioContext)(),
			volume = (context.createGain ? context.createGain() : context.createGainNode());
		volume.connect(context.destination);

		if(!localStorage.global_gain) {
			localStorage.global_gain = volume.gain.value;
		}

		if(!localStorage.global_range) {
			localStorage.global_range = localStorage.global_gain * 100;
		}

		var changeVolume = function() {
			localStorage.global_range = volrange.value;
			localStorage.global_gain = volume.gain.value = volrange.value * 0.01;
			changeIcon(volume.gain.value * 100);
		};

		var changeIcon = function(v) {
			vol.firstElementChild.src = (v > 0 ? 'img/icons/flute.svg' : 'img/icons/flutenb.svg');
			//vol.innerHTML = (v > 0 ? (v > 50 ? 'volume_ off' : 'volume_down') : 'volume_mute');
		};

		vol.onclick = function() {
			volume.gain.value = (volume.gain.value > 0 ? 0 : volrange.value * 0.01);
			localStorage.global_gain = volume.gain.value;
			changeIcon(localStorage.global_gain);
			if(localStorage.global_gain == 0) {
				// global mute stop and remove all currently playing audio buffers
				if(audio){
					Object.keys(audio_sources).forEach(function(key) {
						audio_sources[key].forEach(function(value) { value.stop() });
						audio_sources[key] = [];
					});
				}
			}
		}

		// restore saved volume value at load
		volume.gain.value = localStorage.global_gain;
		volrange.value = localStorage.global_range;
		changeIcon(localStorage.global_gain)

		volrange.oninput = changeVolume;
	};


	// Inventory chest

	chest.addEventListener('mouseover', function(event) {
		chest.firstElementChild.src = 'img/icons/coffreouvert.svg';
		ws.send(JSON.stringify({type: 'inventory'}));
		inventory_display.style.display = "flex";
		bank_display.style.display = "none";
	});

	chest.addEventListener('mouseleave', function(event) {
		event.stopPropagation();
		chest.firstElementChild.src = 'img/icons/coffre.svg';
		inventory_display.style.display = "none";
	});

	bank_display.addEventListener('mouseleave', function(event) {
		event.stopPropagation();
		bank_display.style.display = "none";
	});

	inventory_display.addEventListener('mouseover', function(event) {
		event.stopPropagation();
		bank_display.style.display = "none";
		inventory_display.style.opacity = 1;
	})

	// Items
	function item_dragstart(event) {
		event.target.dataTransfer.setData(event.target.getAttribute('data-id'));
		event.preventDefault();
	}

	function item_dragover(event) {
		event.preventDefault();
	}

	function item_dragenter(event) {
		event.preventDefault();
	}

	function item_drop(event) {
		event.preventDefault();
		target_id = event.target.getAttribute("data-id").split(" ");
		ws.send(JSON.stringify({
			type : 'use',
			object_id: parseInt(dragged_item),
			params : target_id }));
	}

	function use_item() {
		attribute = this.getAttribute('data-id');
		ws.send(JSON.stringify({ type : 'use', object_id: attribute, params : "" }));
		ws.send(JSON.stringify({ type : 'inventory'}));
	}

	function take_item() {
		attribute = this.getAttribute('data-id');
		ws.send(JSON.stringify({ type : 'take', object_id: attribute}));
		ws.send(JSON.stringify({ type : 'channel_inventory'}));
	}

	function display_bank() {
		ws.send(JSON.stringify({type: 'channel_inventory'}));
		inventory_display.style.display = "none";
		bank_display.style.display = bank_display.style.display == "flex" ? "none" : "flex";
	}

	function display_inventory() {
		ws.send(JSON.stringify({type: 'inventory'}));
		chest.firstElementChild.src = 'img/icons/coffreouvert.svg';
		bank_display.style.display = "none";
		inventory_display.style.display = inventory_display.style.display == "flex" ? "none" : "flex";
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

	// wheel turning
	gear.onclick = function myFunction() {
		var wheelTurning = document.getElementById("menu_display");
		wheelTurning.classList.toggle("rotation");
	} 

	// Menu pop-over panel display
	var menugear = document.getElementById('menu_display');
	menugear.onclick = function openMenu() {
		menuOpen = !menuOpen;
		var element = document.getElementById("loult-menu");
		element.classList.toggle("popover-display-false");
	}

	// pokedex (wiki link/last updates)
	var pokedex = document.getElementById('pokedex');

	pokedex.onmouseover = function hover() {
		pokedex.setAttribute('src', 'img/icons/pokedex_on.svg');
	}
	pokedex.onmouseleave = function unhover() {
		pokedex.setAttribute('src', 'img/icons/pokedex.svg');
	}

	async function getLastEdits() {
        let response = await fetch("https://wiki.loult.family/api/last_edits");
		return await response.json();
      }

	pokedex.onclick = function () {
		getLastEdits().then(data => {
			var wikiDisplay = document.getElementById('wiki-last-edits'),
				articlesList = document.getElementById('articles-list');
			wikiDisplay.classList.toggle("popover-display-false")
			// clearing former list
			articlesList.innerHTML = '';
			data.forEach(entry => {
				var entryNode = document.createElement('li');
				var title = document.createElement("h3")
				var titleLink = document.createElement("a")
				titleLink.innerHTML = entry.title;
				titleLink.target = "_blank";
				titleLink.href = "https://wiki.loult.family/page/" + entry.name;
				title.appendChild(titleLink)
				var editor = document.createElement("span");
				editor.style.color = entry.editor.color
				editor.innerHTML = entry.editor.fullname
				var editInfo = document.createElement("p");
				var d = new Date(entry.time), date;
				date = d.toISOString().split('T')[0]
				editInfo.innerHTML = 'Modif par ' + editor.outerHTML + ' le ' + date;
				entryNode.appendChild(title)
				entryNode.appendChild(editInfo)
				articlesList.appendChild(entryNode)
			})
		})
	}


	// WebSocket-related functions

	var wsConnect = function() {
		//ws = new WebSocket(location.origin.replace('http', 'ws') + '/socket' + location.pathname);
		ws = new WebSocket('wss://loult.family/socket/toast');
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
					else if(trimed.match(/^\/(?:en|es|fr|de|it)\s/i)) {
						ws.send(JSON.stringify({type: 'msg', msg: trimed.substr(4), lang: trimed.substr(1, 2).toLowerCase()}));
						underlay.className = 'pulse';
					}
					else if(trimed.match(/^\/(pm|mp) ([a-zA-Z-À-ž]+) ?(\d+)? ?:(.+)/i)) {
						var index = trimed.indexOf(':');
						var msg_content = trimed.substr(index + 1).trim();
						var msg_meta = trimed.substr(0, index).split(' ');

						ws.send(JSON.stringify(
							{ type : 'private_msg',
								msg: msg_content,
								target: msg_meta[1],
								order : ((msg_meta.length === 3) ? parseInt(msg_meta[2]) : 0)
							}
						));
					}
					else if(trimed.match(/^\/((?:bank)+)$/i)) {
						display_bank();
					}
					else if(trimed.match(/^\/((?:list)+)$/i)) {
						display_inventory();
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
					else if(trimed.match(/^\/mod\s/i)) {
						var splitted = trimed.split(' ');
						ws.send(JSON.stringify({ mod : splitted[1], params : splitted.slice(2)}));
					}
					else if(trimed.match(/^\/trash|drop\s/i)) {
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
						addLine({name : 'info'}, '/list : Afficher son inventaire.', d, 'part', 'help');
						addLine({name : 'info'}, '/bank : Afficher l\inventaire public du salon', d, 'part', 'help');
						addLine({name : 'info'}, '/trash : Jeter un objet de son inventaire. Exemple: /trash 3', d, 'part', 'help');
						addLine({name : 'info'}, '/take : Prendre un object dans l\'inventaire public du salon. Exemple: /take 4', d, 'part', 'help');
						addLine({name : 'info'}, '/pm, /mp : Envoyer un message privé. Exemple : /pm Machopeur 2 : On se retrouve 18h à la salle', d, 'part', 'help');
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
			else if(evt.keyCode == 39 && input.value == "") {
				display_inventory();
			}
			else if(evt.keyCode == 37 && input.value == "") {
				display_bank();
			}
		};

		ws.onopen = function() {
			waitTime = 1000;
			updateCookieDisplay();
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
						if (embedbtn.checked==true) {
							//regex to get if msg have youtube link
							let VID_REGEX =/^(?:.*)?((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)(?:.*)??$/gm;
							if (msg.msg.match(VID_REGEX) ) {
								ytbId = '';
								if(msg.msg.match('youtu.be/'))
									ytbId=msg.msg.split(".be/")[1].substring(0, 11);
								else
									ytbId=msg.msg.split("v=")[1].substring(0, 11);
								addEmbedYtb(ytbId,autoscroll);
							}

							//if noelshack URL(just url) link
							if (msg.msg.match('http://image.noelshack.com/')|| msg.msg.match('https://image.noelshack.com/')){
								var imgId=msg.msg.split("noelshack.com/")[1];
								addEmbedNoelshack(imgId,autoscroll);
							}
						}
						break;

					case 'private_msg':
						if(msg.event){
							switch(msg.event) {
								case 'invalid_target':
									addLine({name : 'info'}, 'Utilisateur récepteur inexistant', (new Date), 'kick', 'invalid');
									break;
								case 'success':
									addLine({name : 'info'}, 'Message envoyé avec succès', (new Date), 'info');
							}
						}
						else {
							if(!lastMuted)
								addLine(
									{name : 'info'},
									'MP de ' + users[msg.userid].name + ' ' +
									users[msg.userid].adjective + ' : ' + parser(msg.msg),
									(new Date), msg.type, msg.userid);
						}
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

					case 'inventory' :
						inventory_display.innerHTML = "";
						bank_display.innerHTML = "";

						items = msg['items'];

						if(items.length <= 0) {
							inventory_display.innerHTML = "<span>...</span>";
							bank_display.innerHTML = "<span>...</span>";
							return;
						}

						target_display = msg['owner'] == "user" ? inventory_display : bank_display;
						item_callback = msg['owner'] == "user" ? use_item : take_item;

						for(i = 0; i < items.length; i++) {
							id = items[i]['id'];
							name = items[i]['name'];
							icon = items[i]['icon'];
							item = document.createElement('div');
							item_link = document.createElement('a');
							item_id = document.createElement("span");
							item_img = document.createElement('img');
							item.setAttribute("class", "item");
							item.setAttribute("data-id", id);
							item_img.setAttribute("draggable", true);
							item_link.setAttribute("title", name);
							item_id.innerHTML = id;
							item_img.setAttribute("src", "img/icons/" + icon);
							item_img.setAttribute("data-id", id);
							item_img.addEventListener('drag', function(event) {
								dragged_item = this.getAttribute('data-id');
							});
							item_link.appendChild(item_id);
							item_link.appendChild(item_img);
							item.appendChild(item_link);
							item.addEventListener('click', item_callback, true);
							target_display.appendChild(item);
						}
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
								addLine({name : 'info'}, 'L\'objet ' + msg.object_name + ' a été pris dans l\'inventaire commun.', (new Date), 'log');
								break;
						}
						break;

					case 'punish':
						switch(msg['event']){
							case 'taser':
								ws.close();
								banned = true;
							function sleep(ms) {
								return new Promise(resolve => setTimeout(resolve, ms));
							}
							async function tase(){
								while(true){
									addLine({name : 'info'}, 'CIVILISE TOI FILS DE PUTE', (new Date), 'kick', 'antiflood');
									await sleep(10)
								}
							}
								tase();
								break;

							case 'cactus':
								ws.close();
								ws = null;
								window.location.replace("http://0xad.net/cactus/");
								cactus = true;
								break;
						}
				}
			}
			else if(!lastMuted && audio && volume.gain.value > 0) {
				context.decodeAudioData(msg.data, function(buf) {
					var source = context.createBufferSource();
					source.buffer = buf;
					source.connect(volume);
					// remove node from array once the song is played (or stopped)
					source.onended = function(event) {
						if(audio_sources[lastId] !== undefined) {
							let index = audio_sources[lastId].indexOf(source);
							if(index > -1)
								audio_sources[lastId].splice(index, 1);
						}
					};
					source.start();
					if(typeof audio_sources[lastId] === 'undefined')
						audio_sources[lastId] = [];
					audio_sources[lastId].push(source);
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
=======
            userlist.appendChild(row);
            users[userid].dom = row;
        };

        var delUser = function (userid) {
            userlist.removeChild(users[userid].dom);
            delete users[userid];
        };

        hist = document.getElementById('history'),
            hist.value = localStorage.getItem('history') ? localStorage.getItem('history') : 'full';

        hist.onchange = function () {
            localStorage.history = hist.value;
        }

        // Limit the number of messages displayed
        var limitHistory = function () {
            var limit = localStorage.getItem('history');

            if (limit === 'full' || typeof limit === 'undefined' || !limit) {
                return;
            }

            // var limit = 20;
            var hcount = 0;
            var history = chat.children;

            // increments counter for each messages, just one time for other type of blocks
            for (var i = 0; i < history.length; i++) {
                var cnode = history.item(i);
                if (cnode.classList.contains('msg') || cnode.classList.contains('backlog')) {
                    for (var j = 2; j <= (cnode.childNodes[1].childElementCount); j++) {
                        hcount++;
                    }
                } else {
                    hcount++;
                }
            }

            // removes only the oldest message if block contains several ones
            if (hcount > limit) {
                var node = history.item(0);
                if (node.classList.contains('msg')) {
                    // tightly coupled with current html structure
                    var cnode = node.childNodes[1];
                    if (typeof cnode.childNodes[2] !== 'undefined') {
                        cnode.childNodes[1].remove();
                    } else
                        node.remove();
                } else {
                    node.remove();
                }
            }
        };

        var historycfg = {attributes: false, childList: true, subtree: true};
        var historyObserver = new MutationObserver(limitHistory);
        historyObserver.observe(chat, historycfg);


        // Focus-related functions

        var dontFocus = false;

        var refocus = function (event) {
            if (!dontFocus && !window.getSelection().toString() && !menuOpen)
                input.focus();
        };

        // clicking anywhere on the chat and userlist refocuses to the text input area
        document.body.getElementsByTagName("main")[0].addEventListener('mouseup', refocus, false);

        window.addEventListener('resize', function (evt) {
            chat.scrollTop = chat.scrollHeight;
            refocus();
        });

        window.onfocus = function (event) {
            if (count > 0) {
                document.title = 'Loult.family';
                count = 0;
            }
            refocus();
        };

        // Preferences
        var gear = document.getElementById('gear'),
            embedbtn = document.getElementById('embed'),
            ambtn = document.getElementById('am'),
            head = document.getElementById('head'),
            main = document.getElementById('main'),
            foot = document.getElementById('foot'),
            themes = document.getElementById('theme'),
            poketype = document.getElementById('poketype'),
            colors = document.getElementById('color'),
            fonts = document.getElementById('font'),
            settings = theme.split(' ');

        ambtn.checked = localStorage.getItem('automute') == 'true' ? true : false;
        embedbtn.checked = localStorage.getItem('embed') == 'true' ? true : false;

        ambtn.onchange = function () {
            localStorage.setItem('automute', ambtn.checked);
        }

        embedbtn.onchange = function () {
            localStorage.setItem('embed', embedbtn.checked);
        }


        var applyTheme = function () {
            theme = localStorage.theme = settings.join(' ');
            document.body.className = theme.replace('_', ' ');
            chat.scrollTop = chat.scrollHeight;
        };

        applyTheme();
        themes.value = settings[0];
        colors.value = settings[1];
        fonts.value = settings[2];
        poketype.value = settings[3];

        themes.onchange = function () {
            settings[0] = this.value;
            applyTheme();
        };

        colors.onchange = function () {
            settings[1] = this.value;
            applyTheme();
        };

        fonts.onchange = function () {
            settings[2] = this.value;
            applyTheme();
        };

        poketype.onchange = function () {
            settings[3] = this.value;
            applyTheme();
        };


        // Languages

        var select = document.getElementById('lang'),
            lang = localStorage.lang;

        if (!lang) {
            var ln = navigator.language.substr(0, 2);
            switch (ln) {
                case 'fr':
                case 'es':
                case 'de':
                    lang = ln;
                    break;
                default:
                    lang = 'fr';
            }
            localStorage.lang = lang;
        }

        select.value = lang;

        select.onchange = function () {
            lang = this.value;
            localStorage.lang = lang
        };

        // cookie setting in the menu

        var cookieInput = document.getElementById("cookie"),
            cookieSetButton = document.getElementById("change-cookie");

        function parse_cookie() {
            return document.cookie.split('; ').reduce((prev, current) => {
                const [name, value] = current.split('=');
                prev[name] = value;
                return prev
            }, {});
        }

        var updateCookieDisplay = function () {
            try {
                cookieInput.value = parse_cookie().id;
            } catch (e) {
                console.log("Invalid cookie format. Stick to 'id=yourcookie;'")
            }

        }
        if (document.cookie) {
            updateCookieDisplay()
        }

        cookieSetButton.onclick = function () {
            document.cookie = 'id=' + cookieInput.value + '; SameSite=Strict;';
            ws.close();
        }


        // Sound and volume

        if (audio) {
            var vol = document.getElementById('vol'),
                volrange = document.getElementById('volrange'),
                context = new (window.AudioContext || webkitAudioContext)(),
                volume = (context.createGain ? context.createGain() : context.createGainNode());
            volume.connect(context.destination);

            if (!localStorage.global_gain) {
                localStorage.global_gain = volume.gain.value;
            }

            if (!localStorage.global_range) {
                localStorage.global_range = localStorage.global_gain * 100;
            }

            var changeVolume = function () {
                localStorage.global_range = volrange.value;
                localStorage.global_gain = volume.gain.value = volrange.value * 0.01;
                changeIcon(volume.gain.value * 100);
            };

            var changeIcon = function (v) {
                vol.firstElementChild.src = (v > 0 ? 'img/icons/flute.svg' : 'img/icons/flutenb.svg');
                //vol.innerHTML = (v > 0 ? (v > 50 ? 'volume_ off' : 'volume_down') : 'volume_mute');
            };

            vol.onclick = function () {
                volume.gain.value = (volume.gain.value > 0 ? 0 : volrange.value * 0.01);
                localStorage.global_gain = volume.gain.value;
                changeIcon(localStorage.global_gain);
                if (localStorage.global_gain === 0) {
                    // global mute stop and remove all currently playing audio buffers
                    if (audio) {
                        Object.keys(audio_sources).forEach(function (key) {
                            audio_sources[key].forEach(function (value) {
                                value.stop()
                            });
                            audio_sources[key] = [];
                        });
                    }
                }
            }

            // restore saved volume value at load
            volume.gain.value = localStorage.global_gain;
            volrange.value = localStorage.global_range;
            changeIcon(localStorage.global_gain)

            volrange.oninput = changeVolume;
        }


        // Inventory chest

        chest.addEventListener('click', function (event) {
            if (inventory_display.style.display === "none") {
                chest.firstElementChild.src = 'img/icons/coffreouvert.svg';
                ws.send(JSON.stringify({type: 'inventory'}));
                inventory_display.style.display = "flex";
            } else {
                event.stopPropagation();
                chest.firstElementChild.src = 'img/icons/coffre.svg';
                inventory_display.style.display = "none";
            }
        });

        bank_display.addEventListener('mouseleave', function (event) {
            event.stopPropagation();
            bank_display.style.display = "none";
        });

        inventory_display.addEventListener('mouseover', function (event) {
            event.stopPropagation();
            bank_display.style.display = "none";
            inventory_display.style.opacity = 1;
        })

        // Items
        function item_dragstart(event) {
            event.target.dataTransfer.setData(event.target.getAttribute('data-id'));
            event.preventDefault();
        }

        function item_dragover(event) {
            event.preventDefault();
        }

        function item_dragenter(event) {
            event.preventDefault();
        }

        function item_drop(event) {
            event.preventDefault();
            target_id = event.target.getAttribute("data-id").split(" ");
            ws.send(JSON.stringify({
                type: 'use',
                object_id: parseInt(dragged_item),
                params: target_id
            }));
        }

        function use_item() {
            attribute = this.getAttribute('data-id');
            ws.send(JSON.stringify({type: 'use', object_id: attribute, params: ""}));
            ws.send(JSON.stringify({type: 'inventory'}));
        }

        function take_item() {
            attribute = this.getAttribute('data-id');
            ws.send(JSON.stringify({type: 'take', object_id: attribute}));
            ws.send(JSON.stringify({type: 'channel_inventory'}));
        }

        function display_bank() {
            ws.send(JSON.stringify({type: 'channel_inventory'}));
            inventory_display.style.display = "none";
            bank_display.style.display = bank_display.style.display === "flex" ? "none" : "flex";
        }

        function display_inventory() {
            ws.send(JSON.stringify({type: 'inventory'}));
            chest.firstElementChild.src = 'img/icons/coffreouvert.svg';
            bank_display.style.display = "none";
            inventory_display.style.display = inventory_display.style.display === "flex" ? "none" : "flex";
        }

        // Users list display

        var userswitch = document.getElementById('userlist-toggle');

        userswitch.onclick = function () {
            var atBottom = (chat.scrollTop === (chat.scrollHeight - chat.offsetHeight));
            document.body.classList.toggle("userlist-folded");
            // userlist.style.width = (userlist.style.width === '0px' ? '200px' : '0px');
            // head.style.paddingRight = underlay.style.right = userlist.style.width;
            if (atBottom)
                chat.scrollTop = chat.scrollHeight;
        };

        // wheel turning
        var menugear = document.getElementById('menu-gear-display');
        var menugearToolTip = document.getSelection('#menu-gear-display > span');

        gear.onclick = function () {
            menugear.classList.toggle("rotation");
            menugearToolTip.classList.toggle("hidden");
        }

        // Menu pop-over panel display
        menugear.onclick = function () {
            menuOpen = !menuOpen;
            var element = document.getElementById("loult-menu");
            element.classList.toggle("popover-display-false");
        }

        // pokedex (wiki link/last updates)
        var pokedex = document.getElementById('pokedex');

        pokedex.onmouseover = function hover() {
            pokedex.setAttribute('src', 'img/icons/pokedex_on.svg');
        }
        pokedex.onmouseleave = function unhover() {
            pokedex.setAttribute('src', 'img/icons/pokedex.svg');
        }


        // BNL link
        var bnlLink = document.getElementById('bnl-icon')
        bnlLink.onmouseover = function hover() {
            bnlLink.setAttribute('src', 'img/icons/bnl-open.svg');
        }
        bnlLink.onmouseleave = function unhover() {
            bnlLink.setAttribute('src', 'img/icons/bnl-closed.svg');
        }

        async function getLastEdits() {
            let response = await fetch("https://wiki.loult.family/api/last_edits");
            return await response.json();
        }

        pokedex.onclick = function () {
            getLastEdits().then(data => {
                var wikiDisplay = document.getElementById('wiki-last-edits'),
                    articlesList = document.getElementById('articles-list');
                wikiDisplay.classList.toggle("popover-display-false")
                // clearing former list
                articlesList.innerHTML = '';
                data.forEach(entry => {
                    var entryNode = document.createElement('li');
                    var title = document.createElement("h3")
                    var titleLink = document.createElement("a")
                    titleLink.innerHTML = entry.title;
                    titleLink.target = "_blank";
                    titleLink.href = "https://wiki.loult.family/page/" + entry.name;
                    title.appendChild(titleLink)
                    var editor = document.createElement("span");
                    editor.style.color = entry.editor.color
                    editor.innerHTML = entry.editor.fullname
                    var editInfo = document.createElement("p");
                    var d = new Date(entry.time), date;
                    date = d.toISOString().split('T')[0]
                    editInfo.innerHTML = 'Modif par ' + editor.outerHTML + ' le ' + date;
                    entryNode.appendChild(title)
                    entryNode.appendChild(editInfo)
                    articlesList.appendChild(entryNode)
                })
            })
        }

        // file upload-related functions
        var fileUploadInput = document.getElementById('file-upload');
        var fileUploadIcon = document.getElementById('upload-icon')

        function storeBlob(blob) {
            uploadItemBlob = blob;
            fileUploadIcon.src = 'img/icons/upload-green.svg'
            input.placeholder = '⏎ pour envoyer'
        }

        function resetUpload() {
            uploadItemBlob = undefined;
            fileUploadIcon.src = 'img/icons/upload-grey.svg'
            input.placeholder = 'Message...'
        }


        fileUploadInput.onchange = function () {
            let file = fileUploadInput.files[0];
            storeBlob(file);
        }

        function uploadBlob(callback) {
            let formData = new FormData();
            formData.append("file", uploadItemBlob);
            formData.append("cookie", parse_cookie().id)
            fetch('https://bnl.loult.family/media/upload/multipart',
                {
                    method: "POST",
                    body: formData
                })
                .then(response => {
                    if (response.status !== 200) {
                        throw Error
                    }
                    return response.json()
                })
                .then(callback)
                .catch((error) => {
                    addLine({name: 'info'}, 'Erreur à l\'envoi du fichier', (new Date), 'kick');
                })
        }

        // Audio recording functions

        let microphoneButton = document.getElementById("record"),
            recordingMenu = document.getElementById("record-menu"),
            recordingMenuOpened = false;

        microphoneButton.onclick = function () {
            recordingMenu.classList.toggle("popover-display-false");
            recordingMenuOpened = !recordingMenuOpened;

            if (recordingMenuOpened && navigator.mediaDevices.getUserMedia) {
                console.log('getUserMedia supported.');

                const constraints = {audio: true, video: false},
                    options = {mimeType: 'audio/webm;codecs=opus'};
                let chunks = [];
                let recordedAudioBlob = undefined, playbackSource = undefined;

                let onSuccess = function (stream) {
                    const mediaRecorder = new MediaRecorder(stream, options);

                    mediaRecorder.onstop = function (e) {
                        console.log("data available after MediaRecorder.stop() called.");
                        recordedAudioBlob = new Blob(chunks, {'type': options.mimeType});
                        chunks = [];
                        console.log("recorder stopped");

                    }

                    mediaRecorder.ondataavailable = function (e) {
                        chunks.push(e.data);
                    }

                    var microphoneIcon = document.getElementById("microphone-icon"),
                        recordButton = document.getElementById("record-button"),
                        stopButton = document.getElementById("stop-button"),
                        restartButton = document.getElementById("restart-button"),
                        playButton = document.getElementById("play-button"),
                        pauseButton = document.getElementById("pause-button"),
                        sendButton = document.getElementById("send-button");

                    recordButton.onclick = function () {
                        mediaRecorder.start();
                        console.log(mediaRecorder.state);
                        console.log("recorder started");
                        recordButton.classList.toggle("hidden");
                        stopButton.classList.toggle("hidden");
                        microphoneIcon.classList.toggle("recording-active");
                    }

                    stopButton.onclick = function () {
                        mediaRecorder.stop();
                        console.log(mediaRecorder.state);
                        console.log("recorder stopped");
                        stopButton.classList.toggle("hidden");
                        restartButton.classList.toggle("hidden");
                        microphoneIcon.classList.toggle("recording-active");
                        playButton.removeAttribute('disabled');
                        pauseButton.removeAttribute('disabled');
                        sendButton.removeAttribute('disabled');
                    }

                    restartButton.onclick = function () {
                        recordedAudioBlob = undefined;
                        playbackSource = undefined;
                        restartButton.classList.toggle("hidden");
                        recordButton.classList.toggle("hidden");
                        playButton.classList.remove("hidden");
                        pauseButton.classList.add("hidden");
                        playButton.setAttribute("disabled", "");
                        pauseButton.setAttribute("disabled", "");
                        sendButton.setAttribute("disabled", "");
                    }

                    playButton.onclick = function () {
                        if (recordedAudioBlob === undefined) return;
                        if (playbackSource === undefined) {
                            let fileReader = new FileReader();
                            let arrayBuffer;

                            fileReader.onloadend = () => {
                                arrayBuffer = fileReader.result;
                                context.decodeAudioData(arrayBuffer)
                                    .then(buf => {
                                        playbackSource = context.createBufferSource();
                                        playbackSource.buffer = buf;
                                        playbackSource.connect(volume);
                                        // set the playback node to none once it's finished
                                        playbackSource.onended = function (event) {
                                            playbackSource = undefined
                                            playButton.classList.toggle("hidden");
                                            pauseButton.classList.toggle("hidden");
                                        };
                                        playbackSource.start();
                                    })
                            }

                            fileReader.readAsArrayBuffer(recordedAudioBlob);

                        }

                        playButton.classList.toggle("hidden");
                        pauseButton.classList.toggle("hidden");


                    }

                    pauseButton.onclick = function () {
                        try {
                            playbackSource.stop();
                        } catch (e) {
                            // pass
                        }
                        playButton.classList.toggle("hidden");
                        pauseButton.classList.toggle("hidden");
                    }

                    sendButton.onclick = function () {
                        if (recordedAudioBlob !== undefined) {
                            storeBlob(recordedAudioBlob);
                        }
                    }
                }
                let onError = function (err) {
                    console.log('The following error occured: ' + err);
                }

                navigator.mediaDevices.getUserMedia(constraints).then(onSuccess, onError);

            } else {
                console.log('getUserMedia not supported on your browser!')
            }
        }

        var wsConnect = function () {
            ws = new WebSocket(location.origin.replace('http', 'ws') + '/socket' + location.pathname);
            //ws = new WebSocket('wss://loult.family/socket/toast');
            ws.binaryType = 'arraybuffer';

            var lastMuted = false;

            input.onfocus = function (evt) {
                if (audio && context && context.state !== "running") {
                    context.resume().then(() => {
                        console.log('Playback resumed successfully');
                    });
                }
            }

            input.onpaste = function (pasteEvent) {
                // if the paste is a base64 blob, capture it and store blob
                if (pasteEvent.clipboardData === false) {
                    return
                }

                var items = pasteEvent.clipboardData.items;

                if (items === undefined) {
                    return
                }

                for (let i = 0; i < items.length; i++) {
                    // Skip content if not image
                    if (items[i].type.indexOf("image") === -1) continue;
                    // Retrieve image on clipboard as blob
                    storeBlob(items[i].getAsFile());
                    pasteEvent.preventDefault();
                    return;
                }

            }

            input.onkeydown = function (evt) {
                underlay.className = '';
                if (evt.keyCode === 13 && uploadItemBlob) {
                    uploadBlob(data => {
                        ws.send(JSON.stringify(
                            {
                                type: 'msg',
                                msg: "https://bnl.loult.family" + data.file_path,
                                lang: lang
                            }))
                    });
                    resetUpload();
                }
                if (evt.keyCode === 13 && input.value) {
                    var trimed = input.value.trim();
                    if (trimed.charAt(0) === '/') {
                        if (trimed.match(/^\/at(?:k|q|ta(?:ck|que))\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({
                                type: 'attack',
                                target: splitted[1],
                                order: ((splitted.length === 3) ? parseInt(splitted[2]) : 0)
                            }));
                        } else if (trimed.match(/^\/(?:en|es|fr|de|it)\s/i)) {
                            ws.send(JSON.stringify({
                                type: 'msg',
                                msg: trimed.substr(4),
                                lang: trimed.substr(1, 2).toLowerCase()
                            }));
                            underlay.className = 'pulse';
                        } else if (trimed.match(/^\/(pm|mp) ([a-zA-Z-À-ž]+) ?(\d+)? ?:(.+)/i)) {
                            var index = trimed.indexOf(':');
                            var msg_content = trimed.substr(index + 1).trim();
                            var msg_meta = trimed.substr(0, index).split(' ');

                            ws.send(JSON.stringify(
                                {
                                    type: 'private_msg',
                                    msg: msg_content,
                                    target: msg_meta[1],
                                    order: ((msg_meta.length === 3) ? parseInt(msg_meta[2]) : 0)
                                }
                            ));
                        } else if (trimed.match(/^\/((?:bank)+)$/i)) {
                            display_bank();
                        } else if (trimed.match(/^\/((?:list)+)$/i)) {
                            display_inventory();
                        } else if (trimed.match(/^\/give\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({
                                type: 'give',
                                object_id: parseInt(splitted[1]),
                                target: splitted[2],
                                order: ((splitted.length === 4) ? parseInt(splitted[3]) : 0)
                            }));
                        } else if (trimed.match(/^\/use\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({
                                type: 'use',
                                object_id: parseInt(splitted[1]),
                                params: splitted.slice(2)
                            }));
                        } else if (trimed.match(/^\/take\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({type: 'take', object_id: parseInt(splitted[1])}));
                        } else if (trimed.match(/^\/mod\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({mod: splitted[1], params: splitted.slice(2)}));
                        } else if (trimed.match(/^\/trash|drop\s/i)) {
                            var splitted = trimed.split(' ');
                            ws.send(JSON.stringify({type: 'trash', object_id: parseInt(splitted[1])}));
                        } else if (trimed.match(/^\/vol(?:ume)?\s(?:\d+)$/i) && audio) {
                            volrange.value = Math.min(100, trimed.match(/\d+$/i)[0]);
                            changeVolume();
                        } else if (trimed.match(/^\/(?:help|aide)$/i)) {
                            var d = new Date;
                            addLine({name: 'info'}, '/attaque, /attack, /atq, /atk : Lancer une attaque sur quelqu\'un. Exemple : /attaque Miaouss 2', d, 'part', 'help');
                            addLine({name: 'info'}, '/en, /es, /fr, /de : Envoyer un message dans une autre langue. Exemple : /en Where is Pete Ravi?', d, 'part', 'help');
                            if (audio)
                                addLine({name: 'info'}, '/volume, /vol : Régler le volume rapidement. Exemple : /volume 50', d, 'part', 'help');
                            addLine({name: 'info'}, '/me : Réaliser une action. Exemple: /me essaie la commande /me.', d, 'part', 'help');
                            addLine({name: 'info'}, '/use : Utiliser un object de son inventaire. Exemple: /use 3 Miaouss 2', d, 'part', 'help');
                            addLine({name: 'info'}, '/give : Donner un objet de son inventaire à quelqu\'un d\'autre. Exemple: /give 2 Tauros', d, 'part', 'help');
                            addLine({name: 'info'}, '/list : Afficher son inventaire.', d, 'part', 'help');
                            addLine({name: 'info'}, '/bank : Afficher l\inventaire public du salon', d, 'part', 'help');
                            addLine({name: 'info'}, '/trash : Jeter un objet de son inventaire. Exemple: /trash 3', d, 'part', 'help');
                            addLine({name: 'info'}, '/take : Prendre un object dans l\'inventaire public du salon. Exemple: /take 4', d, 'part', 'help');
                            addLine({name: 'info'}, '/pm, /mp : Envoyer un message privé. Exemple : /pm Machopeur 2 : On se retrouve 18h à la salle', d, 'part', 'help');
                            addLine({name: 'info'}, '> : Indique une citation. Exemple : >Je ne reviendrais plus ici !', d, 'part', 'help');
                            addLine({name: 'info'}, '** ** : Masquer une partie d\'un message. Exemple : Carapuce est un **chic type** !', d, 'part', 'help');
                        } else if (trimed.match(/^\/me\s/i))
                            ws.send(JSON.stringify({type: 'me', msg: trimed.substr(4)}));
                        else if (trimed.match(/^\/(?:poker|flip|omg|drukqs)$/i)) {
                            document.body.className = theme.replace('_', ' ') + ' ' + trimed.substr(1);
                            chat.scrollTop = chat.scrollHeight;
                        } else if (trimed.match(/^\/((?:bisw)+)$/i)) {
                            document.body.className = 'cozy pink comic';
                            chat.scrollTop = chat.scrollHeight;
                        } else {
                            ws.send(JSON.stringify({type: 'msg', msg: trimed, lang: lang}));
                            underlay.className = 'pulse';
                        }
                    } else if (trimed.length) {
                        ws.send(JSON.stringify({type: 'msg', msg: trimed, lang: lang}));
                        underlay.className = 'pulse';
                    }
                    lastMsg = input.value;
                    input.value = '';
                } else if (evt.keyCode === 38 || evt.keyCode === 40) {
                    evt.preventDefault();
                    input.value = (lastMsg && !input.value ? lastMsg : '');
                } else if (evt.keyCode == 39 && input.value == "") {
                    display_inventory();
                } else if (evt.keyCode == 37 && input.value == "") {
                    display_bank();
                }
            };

            ws.onopen = function () {
                waitTime = 1000;
                updateCookieDisplay();
            };

            ws.onmessage = function (msg) {
                if (typeof msg.data === 'string') {
                    msg = JSON.parse(msg.data);
                    lastMuted = (muted.indexOf(msg.userid) !== -1);

                    switch (msg.type) {
                        case 'msg':
                        case 'bot':
                            if (!lastMuted)
                                addLine(users[msg.userid], parser(msg.msg), msg.date, msg.type, msg.userid);
                            if (embedbtn.checked === true && !lastMuted) {
                                //regex to get if msg have youtube link
                                let VID_REGEX = /^(?:.*)?((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)(?:.*)??$/gm;
                                if (msg.msg.match(VID_REGEX)) {
                                    ytbId = '';
                                    if (msg.msg.match('youtu.be/'))
                                        ytbId = msg.msg.split(".be/")[1].substring(0, 11);
                                    else
                                        ytbId = msg.msg.split("v=")[1].substring(0, 11);
                                    addEmbedYtb(ytbId);
                                }

                                //if noelshack URL(just url) link
                                if (msg.msg.match('http://image.noelshack.com/') || msg.msg.match('https://image.noelshack.com/')) {
                                    var imgId = msg.msg.split("noelshack.com/")[1];
                                    addImgEmbed("https://image.noelshack.com/" + imgId);
                                }

                                // if bnl URL (for img)
                                if (msg.msg.includes('https://bnl.loult.family/media/content/image/')) {
                                    addImgEmbed(msg.msg);
                                }
                            }
                            break;

                        case 'private_msg':
                            if (msg.event) {
                                switch (msg.event) {
                                    case 'invalid_target':
                                        addLine({name: 'info'}, 'Utilisateur récepteur inexistant', (new Date), 'kick', 'invalid');
                                        break;
                                    case 'success':
                                        addLine({name: 'info'}, 'Message envoyé avec succès', (new Date), 'info');
                                }
                            } else {
                                if (!lastMuted)
                                    addLine(
                                        {name: 'info'},
                                        'MP de ' + users[msg.userid].name + ' ' +
                                        users[msg.userid].adjective + ' : ' + parser(msg.msg),
                                        (new Date), msg.type, msg.userid);
                            }
                            break;


                        case 'me':
                            if (!lastMuted)
                                addLine({
                                    name: 'info',
                                    color: users[msg.userid].color
                                }, 'Le ' + users[msg.userid].name + ' ' + users[msg.userid].adjective + ' ' + parser(msg.msg), msg.date, 'me', msg.userid);
                            break;

                        case 'connect':
                            addUser(msg.userid, msg.params, msg.profile);
                            if (!lastMuted)
                                addLine({name: 'info'}, 'Un ' + msg.params.name + ' ' + msg.params.adjective + ' apparaît !', msg.date, 'log', msg.type);
                            break;

                        case 'disconnect':
                            if (!lastMuted)
                                addLine({name: 'info'}, 'Le ' + users[msg.userid].name + ' ' + users[msg.userid].adjective + ' s\'enfuit !', msg.date, 'part', msg.type);
                            delUser(msg.userid);
                            break;

                        case 'attack':
                            switch (msg['event']) {
                                case 'attack':
                                    addLine({name: 'info'}, users[msg.attacker_id].name + ' attaque ' + users[msg.defender_id].name + ' !', msg.date, 'log', msg.type);
                                    break;

                                case 'dice':
                                    addLine({name: 'info'}, users[msg.attacker_id].name + ' tire un ' + msg.attacker_dice + ' + (' + msg.attacker_bonus + '), ' + users[msg.defender_id].name + ' tire un ' + msg.defender_dice + ' + (' + msg.defender_bonus + ') !', msg.date, 'log', msg.type);
                                    break;

                                case 'effect':
                                    addLine({name: 'info'}, users[msg.target_id].name + ' est maintenant affecté par l\'effet ' + msg.effect + ' !', msg.date, 'log', msg.type);
                                    if (msg.target_id === you) {
                                        var d = new Date(msg.date);
                                        d.setSeconds(d.getSeconds() + msg.timeout);
                                        setTimeout(function () {
                                            addLine({name: 'info'}, 'L\'effet ' + msg.effect + ' est terminé.', d, 'part', 'expire');
                                        }, msg.timeout * 1000);
                                    }
                                    break;

                                case 'invalid':
                                    addLine({name: 'info'}, 'Impossible d\'attaquer pour le moment, ou pokémon invalide', (new Date), 'kick', 'invalid');
                                    break;

                                case 'nothing':
                                    addLine({name: 'info'}, 'Il ne se passe rien...', msg.date, 'log', msg.type);
                                    break;
                            }
                            break;

                        case 'antiflood':
                            switch (msg['event']) {
                                case 'banned':
                                    addLine({name: 'info'}, 'Le ' + users[msg.flooder_id].name + ' ' + users[msg.flooder_id].adjective + ' était trop faible. Il est libre maintenant.', msg.date, 'kick', msg.type);
                                    break;

                                case 'flood_warning':
                                    addLine({name: 'info'}, 'Attention, la qualité de vos contributions semble en baisse. Prenez une grande inspiration.', msg.date, 'kick', msg.type);
                                    break;
                            }
                            break;

                        case 'wait':
                            addLine({name: 'info'}, 'La connection est en cours. Concentrez-vous quelques instants avant de dire des âneries.', msg.date, 'log', msg.type);
                            break;

                        case 'notification':
                            addLine({name: 'info'}, msg.msg, ("date" in msg) ? msg.date : (new Date), 'info');
                            break;

                        case 'inventory' :
                            inventory_display.innerHTML = "";
                            bank_display.innerHTML = "";

                            items = msg['items'];

                            if (items.length <= 0) {
                                inventory_display.innerHTML = "<span>...</span>";
                                bank_display.innerHTML = "<span>...</span>";
                                return;
                            }

                            target_display = msg['owner'] == "user" ? inventory_display : bank_display;
                            item_callback = msg['owner'] == "user" ? use_item : take_item;

                            for (i = 0; i < items.length; i++) {
                                id = items[i]['id'];
                                name = items[i]['name'];
                                icon = items[i]['icon'];
                                item = document.createElement('div');
                                item_link = document.createElement('a');
                                item_id = document.createElement("span");
                                item_img = document.createElement('img');
                                item.setAttribute("class", "item");
                                item.setAttribute("data-id", id);
                                item_img.setAttribute("draggable", true);
                                item_link.setAttribute("title", name);
                                item_id.innerHTML = id;
                                item_img.setAttribute("src", "img/icons/objects/" + icon);
                                item_img.setAttribute("data-id", id);
                                item_img.addEventListener('drag', function (event) {
                                    dragged_item = this.getAttribute('data-id');
                                });
                                item_link.appendChild(item_id);
                                item_link.appendChild(item_img);
                                item.appendChild(item_link);
                                item.addEventListener('click', item_callback, true);
                                target_display.appendChild(item);
                            }
                            break;

                        case 'userlist':
                            // flushing previous user list just in case
                            for (var i in users)
                                delUser(i);

                            for (var i = 0; i < msg.users.length; i++)
                                addUser(msg.users[i].userid, msg.users[i].params, msg.users[i].profile);
                            break;

                        case 'backlog':
                            for (var i = 0; i < msg.msgs.length; i++)
                                if (msg.msgs[i].type === 'me')
                                    addLine({
                                        name: 'info',
                                        color: msg.msgs[i].user.color
                                    }, 'Le ' + msg.msgs[i].user.name + ' ' + msg.msgs[i].user.adjective + ' ' + parser(msg.msgs[i].msg), msg.msgs[i].date, 'backlog me', msg.msgs[i].userid);
                                else
                                    addLine(msg.msgs[i].user, parser(msg.msgs[i].msg), msg.msgs[i].date, 'backlog ' + msg.msgs[i].type, msg.msgs[i].userid);

                            addLine({name: 'info'}, 'Vous êtes connecté.', (new Date), 'log', 'connected');
                            break;

                        case 'banned':
                            banned = true;
                            ws.close();
                            break;

                        // conditions dedicated to objects
                        case 'give':
                            switch (msg['response']) {
                                case 'invalid_target':
                                    addLine({name: 'info'}, 'Utilisateur récepteur inexistant', (new Date), 'kick', 'invalid');
                                    break;

                                case 'exchanged':
                                    addLine({name: 'info'}, users[msg.sender].name + ' donne ' + msg.obj_name + ' à  ' + users[msg.receiver].name + ".", msg.date, 'log');
                                    break;
                            }
                            break;

                        case 'object':
                            switch (msg['response']) {
                                case 'invalid_id':
                                    addLine({name: 'info'}, 'Indice d\'objet dans l\'inventaire inexistant', (new Date), 'log', 'invalid');
                                    break;

                                case 'object_trashed':
                                    addLine({name: 'info'}, 'L\'objet ' + msg.object_name + ' a été jeté.', (new Date), 'log');
                                    break;

                                case 'object_taken':
                                    addLine({name: 'info'}, 'L\'objet ' + msg.object_name + ' a été pris dans l\'inventaire commun.', (new Date), 'log');
                                    break;
                            }
                            break;

                        case 'punish':
                            switch (msg['event']) {
                                case 'taser':
                                    ws.close();
                                    banned = true;

                                function sleep(ms) {
                                    return new Promise(resolve => setTimeout(resolve, ms));
                                }

                                async function tase() {
                                    while (true) {
                                        addLine({name: 'info'}, 'CIVILISE TOI FILS DE PUTE', (new Date), 'kick', 'antiflood');
                                        await sleep(10)
                                    }
                                }

                                    tase();
                                    break;

                                case 'cactus':
                                    ws.close();
                                    ws = null;
                                    window.location.replace("http://0xad.net/cactus/");
                                    cactus = true;
                                    break;
                            }
                    }
                } else if (!lastMuted && audio && volume.gain.value > 0) {
                    context.decodeAudioData(msg.data, function (buf) {
                        var source = context.createBufferSource();
                        source.buffer = buf;
                        source.connect(volume);
                        // remove node from array once the song is played (or stopped)
                        source.onended = function (event) {
                            if (audio_sources[lastId] !== undefined) {
                                let index = audio_sources[lastId].indexOf(source);
                                if (index > -1)
                                    audio_sources[lastId].splice(index, 1);
                            }
                        };
                        source.start();
                        if (typeof audio_sources[lastId] === 'undefined')
                            audio_sources[lastId] = [];
                        audio_sources[lastId].push(source);
                    });
                }
            };

            ws.onerror = function (e) {
                console.log(['error', e]);
            };

            ws.onclose = function () {
                for (var i in users)
                    delUser(i);

                if (banned)
                    for (var i = 0; i < 500; i++)
                        addLine({name: 'info'}, 'CIVILISE TOI.', (new Date), 'kick');
                else {
                    addLine({name: 'info'}, 'Vous êtes déconnecté.', (new Date), 'part');
                    addLine({name: 'info'}, 'Nouvelle connexion en cours...', (new Date), 'part');
                    waitTime = Math.min(waitTime * 2, 120000);
                    window.setTimeout(wsConnect, waitTime);
                }
            };
        };
        wsConnect();
    }
);
>>>>>>> b8e6321c44dbbec71ed52235601d9119da4161ca
