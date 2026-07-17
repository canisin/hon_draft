"use strict";

var socketio = io();

let tickAudio = document.getElementById( "clock-tick-audio" );
tickAudio.volume = 0.2;
let startDraftAudio = document.getElementById( "start-draft-audio" );
startDraftAudio.volume = 0.2;
let banHeroAudio = document.getElementById( "ban-hero-audio" );
banHeroAudio.volume = 0.2;
let pickHeroAudio = document.getElementById( "pick-hero-audio" );
pickHeroAudio.volume = 0.2;

let lastPlayedAudio = Date.now();
let audioDelay = 3000;
function playAudio( audio, noDelay = true )
{
    let timeSinceAudio = Date.now() - lastPlayedAudio;
    let remainingDelay = audioDelay - timeSinceAudio;
    if ( noDelay || remainingDelay <= 0 )
    {
        audio.play();
        lastPlayedAudio = Date.now();
    }
    else
    {
        setTimeout( () => {
            audio.play();
        }, remainingDelay );
        lastPlayedAudio += audioDelay;
    }
};
function playAudioWithDelay( audio )
{
    playAudio( audio, false );
}

function clickSlot( team, index )
{
    console.log( "clicking slot" );
    socketio.emit( "click-slot", team, index );
};

function dibsHero( stat, index )
{
    console.log( "dibsing hero" );
    socketio.emit( "dibs-hero", stat, index );
};

function vetoHero( stat, index )
{
    console.log( "vetoing hero" );
    socketio.emit( "veto-hero", stat, index );
};

function auxClickHero( event, stat, index )
{
    event.preventDefault();

    switch ( true )
    {
        case event.button == 1: // middle click
        case event.button == 2 && event.altKey: // alt + right click
        case event.button == 2 && event.ctrlKey: // ctrl + right click
            vetoHero( stat, index );
            break;
        case event.button == 2: // right click
            dibsHero( stat, index )
            break;
    }
};

function banHero( stat, index )
{
    console.log( "banning hero" );
    socketio.emit( "ban-hero", stat, index );
};

function pickHero( stat, index )
{
    console.log( "picking hero" );
    socketio.emit( "pick-hero", stat, index );
};

function clickFirstBan( team )
{
    console.log( "clicking first ban" );
    // undo the click to let the server decide
    let checkbox = document.getElementById( `${ team }-first-ban-checkbox` );
    checkbox.checked = !checkbox.checked;
    socketio.emit( "first-ban", team );
};

function clickToggleStat( stat )
{
    console.log( "clicking toggle stat" );
    // undo the click to let the server decide
    let checkbox = document.getElementById( `${ stat }-checkbox` );
    checkbox.checked = !checkbox.checked;
    socketio.emit( "toggle-stat", stat );
};

function startDraft()
{
    socketio.emit( "start-draft" );
};

function cancelDraft()
{
    socketio.emit( "cancel-draft" );
};

function endDraft()
{
    socketio.emit( "end-draft" );
};

let messageForm = document.getElementById( "message-form" );
messageForm.addEventListener( "submit", sendMessage );
function sendMessage( event )
{
    event.preventDefault();

    let input = document.getElementById( "message-input" );
    if( input.value == "" ) return;
    socketio.emit( "message", input.value );
    input.value = "";
};

function setFirstBan( state )
{
    let legionFirstBan = document.getElementById( "legion-first-ban-checkbox" );
    let hellbourneFirstBan = document.getElementById( "hellbourne-first-ban-checkbox" );

    legionFirstBan.checked = state.first_ban == "legion";
    hellbourneFirstBan.checked = state.first_ban == "hellbourne";
};

function setTeamStatus( state, team )
{
    let teamDiv = document.getElementById( team );
    let arrows = teamDiv.getElementsByClassName( "team-status-arrow" );
    let title = teamDiv.getElementsByClassName( "team-status-label" )[ 0 ];
    let subtitle = teamDiv.getElementsByClassName( "team-status-subtitle" )[ 0 ];

    if ( state.state == "banning" && team == state.active_team )
    {
        Array.from( arrows ).forEach( arrow => arrow.src = "/static/images/arrow-red.png" );
        title.innerHTML = "Banning";
        title.style.color = "red";
        subtitle.innerHTML = "";
        subtitle.style.color = "";
    }
    else if ( state.state == "picking" && team == state.active_team )
    {
        Array.from( arrows ).forEach( arrow => arrow.src = "/static/images/arrow-green.png" );
        title.innerHTML = "Picking";
        title.style.color = "green";
        subtitle.innerHTML = `(Remaining Picks: ${ state.remaining_picks })`;
        subtitle.style.color = "green";
    }
    else
    {
        Array.from( arrows ).forEach( arrow => arrow.src = "" );
        title.innerHTML = "";
        title.style.color = "";
        subtitle.innerHTML = "";
        subtitle.style.color = "";
    }
};

function setStatToggles( state )
{
    for ( let stat in state.stats )
    {
        let is_enabled = state.stats[ stat ];

        let checkbox = document.getElementById( `${ stat }-checkbox` );
        checkbox.checked = is_enabled;

        let statDiv = document.getElementById( stat );
        let label = statDiv.getElementsByClassName( "stat-header-name" )[ 0 ];
        label.style.textDecoration = is_enabled ? "" : "line-through";
    }
};

function setHeroButtons( state )
{
    if ( state.state == "banning" && state.active_team == client_team )
    {
        Array.from( document.getElementsByClassName( "ban-hero-button" ) ).forEach( banButton => banButton.style.display = "" );
        Array.from( document.getElementsByClassName( "pick-hero-button" ) ).forEach( pickButton => pickButton.style.display = "none" );
    }
    else if ( state.state == "picking" && state.active_team == client_team )
    {
        Array.from( document.getElementsByClassName( "ban-hero-button" ) ).forEach( banButton => banButton.style.display = "none" );
        Array.from( document.getElementsByClassName( "pick-hero-button" ) ).forEach( pickButton => pickButton.style.display = "" );
    }
    else
    {
        Array.from( document.getElementsByClassName( "ban-hero-button" ) ).forEach( banButton => banButton.style.display = "none" );
        Array.from( document.getElementsByClassName( "pick-hero-button" ) ).forEach( pickButton => pickButton.style.display = "none" );
    }
};

let current_state = null;
let client_id = null;
let client_team = null;

function isClientObserver()
{
    return client_team == "observers";
};

function onUpdateState( state )
{
    console.log( "changing state" );
    current_state = state.state;

    let stateLabel = document.getElementById( "state" );
    stateLabel.innerHTML = state.state_label;

    let countdownLabel = document.getElementById( "countdown" );
    countdownLabel.style.visibility = ( state.state == "lobby" || state.state == "results" ) ? "hidden" : "visible";

    let startDraftButton = document.getElementById( "start-draft-button" );
    startDraftButton.disabled = state.state != "lobby";

    let cancelDraftButton = document.getElementById( "cancel-draft-button" );
    cancelDraftButton.disabled = [ "lobby", "results" ].includes( state.state );

    let endDraftButton = document.getElementById( "end-draft-button" );
    endDraftButton.disabled = state.state != "results";

    if ( state.state == "banning_countdown" )
    {
        playAudio( startDraftAudio );
    }

    if ( state.state == "banning" && state.active_team == client_team )
    {
        playAudioWithDelay( banHeroAudio );
    }

    if ( state.state == "picking" && state.active_team == client_team )
    {
        playAudioWithDelay( pickHeroAudio );
    }

    setFirstBan( state );
    setTeamStatus( state, "legion" );
    setTeamStatus( state, "hellbourne" );
    setStatToggles( state );
    setHeroButtons( state );
};
socketio.on( "update-state", onUpdateState );

function onUpdateClientId( id )
{
    console.log( "updating client id" );
    client_id = id;
};
socketio.on( "update-client-id", onUpdateClientId );

function onUpdateClientTeam( team )
{
    console.log( "updating client team" );
    client_team = team;
};
socketio.on( "update-client-team", onUpdateClientTeam );

let timer;
function onSetTimer( seconds )
{
    console.log( "setting timer" );

    let countdownLabel = document.getElementById( "countdown" );

    let tick = () => {
        countdownLabel.innerHTML = seconds;

        if ( seconds > 0 )
        {
            if ( current_state == "pool_countdown" )
            {
                tickAudio.play();
            }

            --seconds;
        }
        else
        {
            clearInterval( timer );
        }
    };

    clearInterval( timer );
    tick();
    timer = setInterval( tick, 1000 );
};
socketio.on( "set-timer", onSetTimer );

function setFontSizeToFit( element )
{
    let words = element.textContent.split( " " );
    if ( words.length == 0 ) return;
    let longestWord = words.sort( ( a, b ) => b.length - a.length )[ 0 ];
    let scale = Math.min( 1, 6 / longestWord.length );
    if ( scale == 1 ) return;
    const fontSize = 18;
    element.style.fontSize = ( fontSize * scale ) + "px";
};

Array.from( document.getElementsByClassName( "hero-name" ) ).forEach( setFontSizeToFit );

function calcVetoCountString( hero )
{
    if ( !hero )
    {
        return "";
    }

    if ( isClientObserver() )
    {
        let legionVetoCount = hero.legion_vetos.length;
        let hellbourneVetoCount = hero.hellbourne_vetos.length;
        if ( legionVetoCount == 0 && hellbourneVetoCount == 0 )
        {
            return "";
        }

        return `${ legionVetoCount } / ${ hellbourneVetoCount }`
    }
    else
    {
        let vetoCount = hero[ `${ client_team }_vetos` ].length;
        if ( vetoCount == 0 )
        {
            return "";
        }

        return `${ vetoCount }`;
    }
}

function onUpdateHero( stat, index, hero )
{
    console.log( "updating hero" );
    let heroDiv = document.getElementById( `${ stat }-${ index }` );
    let heroName = heroDiv.getElementsByClassName( "hero-name" )[ 0 ];
    heroName.innerHTML = hero ? hero.name : "";
    setFontSizeToFit( heroName );
    let heroIcon = heroDiv.getElementsByClassName( "hero-icon" )[ 0 ];
    heroIcon.src = `/static/images/${ hero ? hero.path : "hero-none" }.png`;
    heroIcon.style.filter = hero && hero.is_picked ? "grayscale( 1 )" : "";
    let bannedIcon = heroDiv.getElementsByClassName( "hero-icon-banned" )[ 0 ];
    bannedIcon.style.visibility = hero && hero.is_banned ? "visible" : "hidden";
    let vetoCount = heroDiv.getElementsByClassName( "hero-veto-count" )[ 0 ];
    vetoCount.innerHTML = calcVetoCountString( hero );
    let heroSound = heroDiv.getElementsByClassName( "hero-sound" )[ 0 ];
    heroSound.src = hero ? `/static/sounds/${ hero.path }.ogg` : "";
    heroSound.volume = 0.2;
};
socketio.on( "update-hero", onUpdateHero );

function shouldShowHero( slot, team )
{
    if ( !slot.hero )
    {
        return false;
    }

    if ( !slot.is_dibs )
    {
        return true;
    }

    if ( isClientObserver() )
    {
        return true;
    }

    return team == client_team;
};

function onUpdateSlot( team, index, slot )
{
    console.log( "updating slot" );
    let slotDiv = document.getElementById( `${ team }-${ index }` );
    if ( !slot )
    {
        slotDiv.classList.add( "empty-slot" );
    }
    else
    {
        slotDiv.classList.remove( "empty-slot" );
    }

    let isClient = slot && slot.player_id == client_id;
    if ( isClient )
    {
        slotDiv.classList.add( "client-slot" );
    }
    else
    {
        slotDiv.classList.remove( "client-slot" );
    }

    let playerName = slotDiv.getElementsByClassName( "slot-player-name" )[ 0 ];
    playerName.innerHTML = slot ? slot.player_name : "Empty";

    let heroName = slotDiv.getElementsByClassName( "slot-hero-name" )[ 0 ];
    let heroIcon = slotDiv.getElementsByClassName( "slot-hero-icon" )[ 0 ];

    if ( !slot )
    {
        heroName.innerHTML = "";
        heroIcon.src = `/static/images/slot-${ team }.png`;
        heroIcon.style.filter = "";
    }
    else if ( shouldShowHero( slot, team ) )
    {
        heroName.innerHTML = slot.hero.name;
        heroIcon.src = `/static/images/${ slot.hero.path }.png`;
        heroIcon.style.filter = slot.is_dibs ? "grayscale( 1 )" : "";
    }
    else
    {
        heroName.innerHTML = "None";
        heroIcon.src = `/static/images/hero-none.png`;
        heroIcon.style.filter = "";
    }
};
socketio.on( "update-slot", onUpdateSlot );

function onHeroPicked( stat, index )
{
    let heroDiv = document.getElementById( `${ stat }-${ index }` );
    let heroSound = heroDiv.getElementsByClassName( "hero-sound" )[ 0 ];
    playAudioWithDelay( heroSound );
};
socketio.on( "hero-picked", onHeroPicked );

// TODO: This should be doable via css
// TODO: Colors should also be removed from python code
function getTeamColor( team )
{
    switch ( team )
    {
        case "legion":
            return "green";
        case "hellbourne":
            return "red";
        case "observers":
            return "blue";
    }
}

function getTeamIcon( team )
{
    switch ( team )
    {
        case "legion":
            return "team-legion";
        case "hellbourne":
            return "team-hellbourne";
        case "observers":
            return "observer";
    }
}

function updatePlayer( player )
{
    console.log( `updating player id=${ player.id } name=${ player.name } team=${ player.team }` )

    let playerDiv = document.getElementById( player.id );
    let isClient = player.id == client_id;
    if ( isClient )
    {
        playerDiv.classList.add( "client-player" );
    }
    else
    {
        playerDiv.classList.remove( "client-player" );
    }

    let playerName = playerDiv.getElementsByClassName( "players-list-name" )[ 0 ];
    playerName.innerHTML = player.name;
    playerName.style.color = getTeamColor( player.team );
    let playerIcon = playerDiv.getElementsByClassName( "players-list-icon" )[ 0 ];
    playerIcon.src = `/static/images/${ getTeamIcon( player.team ) }.png`;
};

function onUpdatePlayers( players )
{
    let playerList = document.getElementById( "players-list" );
    playerList.innerHTML = "";
    for ( let index in players )
    {
        let player = players[ index ];

        playerList.innerHTML += `
            <div class="players-list-item" id="${ player.id }">
                <img class="players-list-icon"/>
                <div class="players-list-name"/>
            </div>
        `;

        updatePlayer( player );
    }
};
socketio.on( "update-players", onUpdatePlayers );

function onUpdatePlayer( player )
{
    console.log( `updating player ${ player.name }-${ player.id }` );
    updatePlayer( player );
};
socketio.on( "update-player", onUpdatePlayer );

function getTimestamp()
{
    let time = new Date();
    return time.getHours().toString().padStart( 2, "0" )
            + ":"
            + time.getMinutes().toString().padStart( 2, "0" )
            + ":"
            + time.getSeconds().toString().padStart( 2, "0" );
};

function onMessage( message )
{
    console.log( "message received" );
    let messageLog = document.getElementById( "message-log" );
    messageLog.innerHTML += `
        <div class="message">
            <span class="message-timestamp">${ getTimestamp() }</span>
            <span class="message-message">${ message }</span>
        </div>
    `;
    messageLog.scrollTop = messageLog.scrollHeight;
};
socketio.on( "message", onMessage );

function onSetName( name )
{
    console.log( "requesting name change" );
    let form = new FormData();
    form.append( "name", name );
    fetch( "name", { method: "POST", body: form } );
};
socketio.on( "set-name", onSetName );
