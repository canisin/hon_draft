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

let client_id = null;
let client_team = null;

function isClientObserver()
{
    return client_team == "observers";
};

let state = null;
function onUpdateState( new_state )
{
    console.log( "changing state" );
    state = new_state;

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
            if ( state.state == "pool_countdown" )
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
    const fontSize = 18;
    element.style.fontSize = ( fontSize * scale ) + "px";
};

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

function updateHero( stat, index, hero )
{
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
}

function shouldShowDibs( team )
{
    return isClientObserver() || team == client_team;
};

function updateSlot( team, index, player )
{
    let slotDiv = document.getElementById( `${ team }-${ index }` );
    if ( !player )
    {
        slotDiv.classList.add( "empty-slot" );
    }
    else
    {
        slotDiv.classList.remove( "empty-slot" );
    }

    let isClient = player && player.id == client_id;
    if ( isClient )
    {
        slotDiv.classList.add( "client-slot" );
    }
    else
    {
        slotDiv.classList.remove( "client-slot" );
    }

    let playerName = slotDiv.getElementsByClassName( "slot-player-name" )[ 0 ];
    playerName.innerHTML = player ? player.name : "Empty";

    let heroName = slotDiv.getElementsByClassName( "slot-hero-name" )[ 0 ];
    let heroIcon = slotDiv.getElementsByClassName( "slot-hero-icon" )[ 0 ];

    if ( !player )
    {
        heroName.innerHTML = "";
        heroIcon.src = `/static/images/slot-${ team }.png`;
        heroIcon.style.filter = "";
    }
    else if ( player.hero )
    {
        let hero = findHero( player.hero );
        heroName.innerHTML = hero.name;
        heroIcon.src = `/static/images/${ hero.path }.png`;
        heroIcon.style.filter = "";
    }
    else if ( player.dibs && shouldShowDibs( team ) )
    {
        let dibs = findHero( player.dibs );
        heroName.innerHTML = dibs.name;
        heroIcon.src = `/static/images/${ dibs.path }.png`;
        heroIcon.style.filter = "grayscale( 1 )";
    }
    else
    {
        heroName.innerHTML = "None";
        heroIcon.src = `/static/images/hero-none.png`;
        heroIcon.style.filter = "";
    }
};

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

    let [ team, index ] = findPlayer( player.id );
    if ( team != "observers" )
    {
        updateSlot( team, index, player );
    }
};

function findHeroIndex( hero )
{
    for ( let stat in heroes )
    {
        let index = heroes[ stat ].findIndex( ( h ) => h.name == hero );
        if ( index < 0 )
        {
            continue;
        }

        return [ stat, index ];
    }

    console.log( `hero ${ hero } not in heroes` );
};

function findHero( hero )
{
    let [ stat, index ] = findHeroIndex( hero );
    return heroes[ stat ][ index ];
}

function findPlayer( player )
{
    for ( let team in teams )
    {
        let index = teams[ team ].findIndex( ( p ) => p == player );
        if ( index < 0 )
        {
            continue;
        }

        return [ team, index ];
    }

    return [ "observers", 0 ];
};

function onUpdateHero( hero )
{
    console.log( `updating hero ${ hero.name }` );
    let [ stat, index ] = findHeroIndex( hero.name );
    heroes[ stat ][ index ] = hero;
    updateHero( stat, index, hero );
};
socketio.on( "update-hero", onUpdateHero );

let heroes = null;
function onUpdateHeroes( new_heroes )
{
    console.log( "updating heroes" );
    heroes = new_heroes;
    for ( let stat in heroes )
    {
        for ( let index = 0; index < heroes[ stat ].length; ++index )
        {
            updateHero( stat, index, heroes[ stat ][ index ] );
        }
    }
};
socketio.on( "update-heroes", onUpdateHeroes );

function onHeroPicked( hero )
{
    let [ stat, index ] = findHeroIndex( hero );
    let heroDiv = document.getElementById( `${ stat }-${ index }` );
    let heroSound = heroDiv.getElementsByClassName( "hero-sound" )[ 0 ];
    playAudioWithDelay( heroSound );
};
socketio.on( "hero-picked", onHeroPicked );

function onUpdatePlayer( player )
{
    console.log( `updating player ${ player.name }-${ player.id }` );
    players[ player.id ] = player;
    updatePlayer( player );
};
socketio.on( "update-player", onUpdatePlayer );

let players = null;
function onUpdatePlayers( new_players )
{
    console.log( "updating all players" );
    players = new_players;

    let playerList = document.getElementById( "players-list" );
    playerList.innerHTML = "";
    for ( let player in players )
    {
        player = players[ player ]
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

let teams = null;
function onUpdateTeams( new_teams )
{
    teams = new_teams;
    for ( let team in teams )
    {
        for ( let index = 0; index < teams[ team ].length; ++index )
        {
            let player = teams[ team ][ index ];
            updateSlot( team, index, player ? players[ player ] : null );
        }
    }
};
socketio.on( "update-teams", onUpdateTeams );

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
