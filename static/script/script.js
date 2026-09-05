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
let startGameAudio = document.getElementById( "start-game-audio" );
startGameAudio.volume = 0.2;
let counterPickAudio = document.getElementById( "counter-pick-audio" );
counterPickAudio.volume = 0.2;

let lastPlayedAudio = Date.now();
let audioDelay = 3000;
function playAudio( audio )
{
    audio.play();
    lastPlayedAudio = Date.now();
};

function playAudioWithDelay( audio, delay = audioDelay )
{
    let timeSinceAudio = Date.now() - lastPlayedAudio;
    let remainingDelay = delay - timeSinceAudio;
    if ( remainingDelay <= 0 )
    {
        playAudio( audio );
    }
    else
    {
        setTimeout( () => {
            audio.play();
        }, remainingDelay );
        lastPlayedAudio += delay;
    }
};

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

function createPlayerEntry( player, classPrefix )
{
    let entry = document.createElement( "div" );
    entry.className = classPrefix;
    entry.classList.add( `team-${ player.team }` );

    let icon = document.createElement( "img" );
    icon.className = `${ classPrefix }-icon`;
    icon.src = `/static/images/${ getTeamIcon( player.team ) }.png`;
    entry.appendChild( icon );

    let name = document.createElement( "span" );
    name.className = `${ classPrefix }-name`;
    name.textContent = player.name;
    entry.appendChild( name );

    return entry;
};

function updateHeroInformationStatus( hero )
{
    let heroInformation = document.getElementById( "hero-information" );
    heroInformation.classList.remove( "banned", "picked" );

    if ( !hero )
    {
        return;
    }

    if ( hero.is_banned )
    {
        heroInformation.classList.add( "banned" );
        return;
    }

    if ( !players )
    {
        return;
    }

    if ( hero.is_picked )
    {
        heroInformation.classList.add( "picked" );
        let picker = document.getElementById( "hero-information-status-picker" );
        let player = Object.values( players ).find( p => p.hero == hero.name );
        picker.replaceChildren( createPlayerEntry( player, "hero-information-player-entry" ) );
    }
};

function updateHeroInformationDibs( hero )
{
    let dibsDiv = document.getElementById( "hero-information-dibs" );
    dibsDiv.classList.add( "empty" );
    let dibsList = document.getElementById( "hero-information-dibs-list" );
    dibsList.replaceChildren();

    if ( !hero )
    {
        return;
    }

    if ( !players )
    {
        return;
    }

    let dibsPlayers = Object.values( players ).filter( p => p.dibs == hero.name && shouldShowDibs( p.team ) );
    if ( dibsPlayers.length == 0 )
    {
        return;
    }

    dibsDiv.classList.remove( "empty" );
    for ( let player of dibsPlayers )
    {
        dibsList.appendChild( createPlayerEntry( player, "hero-information-player-entry" ) );
    }
};

function updateHeroInformationVeto( hero )
{
    let vetoDiv = document.getElementById( "hero-information-veto" );
    vetoDiv.classList.add( "empty" );
    let vetoList = document.getElementById( "hero-information-veto-list" );
    vetoList.replaceChildren();

    if ( !hero )
    {
        return;
    }

    if ( !players )
    {
        return;
    }

    let vetos = [];
    for ( let team of [ "legion", "hellbourne" ] )
    {
        if ( !shouldShowDibs( team ) )
        {
            continue;
        }

        for ( let [ player, count ] of Object.entries( hero[ `${ team }_vetos` ] ) )
        {
            vetos.push( { player: players[ player ], count } );
        }
    }

    if ( vetos.length == 0 )
    {
        return;
    }

    vetoDiv.classList.remove( "empty" );
    for ( let { player, count } of vetos )
    {
        let entry = createPlayerEntry( player, "hero-information-player-entry" );
        if ( count > 1 )
        {
            let countSpan = document.createElement( "span" );
            countSpan.className = "hero-information-player-entry-veto-count";
            countSpan.textContent = `x ${ count }`;
            entry.appendChild( countSpan );
        }
        vetoList.appendChild( entry );
    }
};

let hoveredHeroPosition = null;
function updateHoveredHero()
{
    let hero = hoveredHeroPosition && heroes
        ? heroes[ hoveredHeroPosition.stat ][ hoveredHeroPosition.index ]
        : null;

    if ( hero )
    {
        let heroInformation = document.getElementById( "hero-information" );
        heroInformation.classList.remove( "no-hero-selected" );
    }
    else
    {
        let heroInformation = document.getElementById( "hero-information" );
        heroInformation.classList.add( "no-hero-selected" );
    }

    let heroIcon = document.getElementById( "hero-information-icon" );
    heroIcon.src = `/static/images/${ hero ? hero.path : "hero-none" }.png`;
    let vetoCount = document.getElementById( "hero-information-veto-count" );
    vetoCount.textContent = calcVetoCountString( hero );

    let heroName = document.getElementById( "hero-information-name" );
    heroName.textContent = hero ? hero.name : "";

    updateHeroInformationStatus( hero );
    updateHeroInformationDibs( hero );
    updateHeroInformationVeto( hero );
};
mouseLeaveHero(); // Initialize to empty state

function mouseEnterHero( event, stat, index )
{
    hoveredHeroPosition = { stat, index };
    updateHoveredHero();
};

function mouseLeaveHero( event, stat, index )
{
    hoveredHeroPosition = null;
    updateHoveredHero();
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

function pauseTimer()
{
    socketio.emit( "pause-timer" );
};

function resumeTimer()
{
    socketio.emit( "resume-timer" );
};

function extendTimer()
{
    socketio.emit( "extend-timer" );
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

function setFirstBan()
{
    let legionFirstBan = document.getElementById( "legion-first-ban-checkbox" );
    let hellbourneFirstBan = document.getElementById( "hellbourne-first-ban-checkbox" );

    legionFirstBan.checked = state.first_ban == "legion";
    hellbourneFirstBan.checked = state.first_ban == "hellbourne";
};

function setTeamStatus( team )
{
    let teamDiv = document.getElementById( team );
    let title = teamDiv.getElementsByClassName( "team-status-label" )[ 0 ];
    let subtitle = teamDiv.getElementsByClassName( "team-status-subtitle" )[ 0 ];

    if ( state.state == "banning" && team == state.active_team )
    {
        title.textContent = "Banning";
        subtitle.textContent = "";
    }
    else if ( state.state == "picking" && team == state.active_team )
    {
        title.textContent = "Picking";
        subtitle.textContent = `(Remaining Picks: ${ state.remaining_picks })`;
    }
    else
    {
        title.textContent = "";
        subtitle.textContent = "";
    }
};

function setStatToggles()
{
    for ( let [ stat, isEnabled ] of Object.entries( state.stats ) )
    {
        let checkbox = document.getElementById( `${ stat }-checkbox` );
        checkbox.checked = isEnabled;

        let statDiv = document.getElementById( stat );
        statDiv.classList.toggle( "disabled", !isEnabled );
    }
};

let clientId = null;
let clientTeam = null;

function isClientObserver()
{
    return clientTeam == "observers";
};

function isClientTeamActive()
{
    return state && clientTeam == state.active_team;
};

function checkAnnouncer( previousState )
{
    // if the previous state was null, then the client is just loading in or refreshing the page
    let isRefresh = !previousState;

    let stateHasChanged = !isRefresh && state.state != previousState.state;
    let teamHasChanged = !isRefresh && state.active_team != previousState.active_team;

    // start draft and result announcements are only played if the client sees the state transition
    let shouldPlayTransition = stateHasChanged;

    // active team announcements are played on refresh and turn changes
    let shouldPlayActiveState = ( isRefresh || stateHasChanged || teamHasChanged ) && isClientTeamActive();

    if ( shouldPlayTransition && state.state == "banning_countdown" )
    {
        playAudio( startDraftAudio );
    }

    if ( shouldPlayActiveState && state.state == "banning" )
    {
        playAudioWithDelay( banHeroAudio );
    }

    if ( shouldPlayActiveState && state.state == "picking" )
    {
        playAudioWithDelay( pickHeroAudio );
    }

    if ( shouldPlayTransition && state.state == "results" )
    {
        playAudioWithDelay( startGameAudio );
    }
};

let state = null;
function onUpdateState( newState )
{
    console.log( "changing state" );
    let previousState = state;
    state = newState;

    document.body.classList.remove( ...Array.from( document.body.classList ).filter( cls => cls.startsWith( "state-" ) ) );
    document.body.classList.add( `state-${ state.state }` );

    document.body.classList.remove( ...Array.from( document.body.classList ).filter( cls => cls.startsWith( "active-team-" ) ) );
    if ( state.active_team )
    {
        document.body.classList.add( `active-team-${ state.active_team }` );
    }

    document.body.classList.toggle( "client-team-active", isClientTeamActive() );

    let stateLabel = document.getElementById( "state" );
    stateLabel.innerHTML = localize( state.state );

    let startDraftButton = document.getElementById( "start-draft-button" );
    startDraftButton.disabled = state.state != "lobby";

    let cancelDraftButton = document.getElementById( "cancel-draft-button" );
    cancelDraftButton.disabled = [ "lobby", "results" ].includes( state.state );

    let endDraftButton = document.getElementById( "end-draft-button" );
    endDraftButton.disabled = state.state != "results";

    setTimer();
    setFirstBan();
    setTeamStatus( "legion" );
    setTeamStatus( "hellbourne" );
    setStatToggles();
    checkAnnouncer( previousState );
};
socketio.on( "update-state", onUpdateState );

function onUpdateClientId( id )
{
    console.log( "updating client id" );
    clientId = id;
};
socketio.on( "update-client-id", onUpdateClientId );

function onUpdateClientTeam( team )
{
    console.log( "updating client team" );
    clientTeam = team;
    document.body.classList.remove( "client-team-legion", "client-team-hellbourne", "client-team-observers" );
    document.body.classList.add( `client-team-${ team }` );
    document.body.classList.toggle( "client-team-active", isClientTeamActive() );
};
socketio.on( "update-client-team", onUpdateClientTeam );

const tickAudioSeconds = 3;
function shouldPlayTickAudio( seconds )
{
    if ( state.state == "pool_countdown" )
    {
        return true;
    }

    if ( [ "banning", "picking" ].includes( state.state ) )
    {
        return seconds <= tickAudioSeconds;
    }
 
    return false;
};

let timer;
function setTimer()
{
    document.body.classList.remove( ...Array.from( document.body.classList ).filter( cls => cls.startsWith( "timer-" ) ) );

    if ( !state.timer )
    {
        return;
    }

    document.body.classList.add( `timer-${ state.timer.state }` );

    console.log( "setting timer" );
    let seconds = Math.ceil( state.timer.seconds );
    let countdownLabel = document.getElementById( "countdown" );

    let tick = () => {
        countdownLabel.textContent = seconds;

        if ( seconds > 0 )
        {
            if ( shouldPlayTickAudio( seconds ) )
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

    if ( state.timer.state == "running" )
    {
        timer = setInterval( tick, 1000 );
    }
};

function setFontSizeToFit( element )
{
    let words = element.textContent.split( " " );
    if ( words.length == 0 ) return;
    let longestWord = words.sort( ( a, b ) => b.length - a.length )[ 0 ];
    let scale = Math.min( 1, 2 / words.length, 6 / longestWord.length );
    const fontSize = 18;
    element.style.fontSize = ( fontSize * scale ) + "px";
};

function calcVetoCountString( hero )
{
    if ( !hero )
    {
        return "";
    }

    let sumVotes = vetos => Object.values( vetos ).reduce( ( a, b ) => a + b, 0 );

    if ( isClientObserver() )
    {
        let legionVetoCount = sumVotes( hero.legion_vetos );
        let hellbourneVetoCount = sumVotes( hero.hellbourne_vetos );
        if ( legionVetoCount == 0 && hellbourneVetoCount == 0 )
        {
            return "";
        }

        return `${ legionVetoCount } / ${ hellbourneVetoCount }`
    }
    else
    {
        let vetoCount = sumVotes( hero[ `${ clientTeam }_vetos` ] );
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
    heroDiv.classList.toggle( "banned", hero && hero.is_banned );
    heroDiv.classList.toggle( "picked", hero && hero.is_picked );
    let heroName = heroDiv.getElementsByClassName( "hero-name" )[ 0 ];
    heroName.textContent = hero ? hero.name : "";
    setFontSizeToFit( heroName );
    let heroIcon = heroDiv.getElementsByClassName( "hero-icon" )[ 0 ];
    heroIcon.src = `/static/images/${ hero ? hero.path : "hero-none" }.png`;
    let vetoCount = heroDiv.getElementsByClassName( "hero-veto-count" )[ 0 ];
    vetoCount.textContent = calcVetoCountString( hero );
    let heroSound = heroDiv.getElementsByClassName( "hero-sound" )[ 0 ];
    heroSound.src = hero ? `/static/sounds/${ hero.path }.ogg` : "";
    heroSound.volume = 0.2;

    updateHoveredHero( hero );
}

function shouldShowDibs( team )
{
    return isClientObserver() || team == clientTeam;
};

function updateTeamSlots( team )
{
    if ( team == "observers" )
    {
        return;
    }

    if ( !teams )
    {
        return;
    }

    for ( let [ index, player ] of teams[ team ].entries() )
    {
        updateSlot( team, index, player ? players[ player ] : null );
    }
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

    let isClient = player && player.id == clientId;
    if ( isClient )
    {
        slotDiv.classList.add( "client-slot" );
    }
    else
    {
        slotDiv.classList.remove( "client-slot" );
    }

    let playerName = slotDiv.getElementsByClassName( "slot-player-name" )[ 0 ];
    playerName.textContent = player ? player.name : "Empty";

    let heroName = slotDiv.getElementsByClassName( "slot-hero-name" )[ 0 ];
    let heroIcon = slotDiv.getElementsByClassName( "slot-hero-icon" )[ 0 ];

    let isDibs = player && !player.hero && player.dibs && shouldShowDibs( team );
    slotDiv.classList.toggle( "dibs", isDibs );

    updateSwapRequests( slotDiv, team, index, player );

    if ( !player )
    {
        heroName.textContent = "";
        heroIcon.src = `/static/images/slot-${ team }.png`;
    }
    else if ( player.hero )
    {
        let hero = findHero( player.hero );
        heroName.textContent = hero.name;
        heroIcon.src = `/static/images/${ hero.path }.png`;
    }
    else if ( isDibs )
    {
        let dibs = findHero( player.dibs );
        heroName.textContent = dibs.name;
        heroIcon.src = `/static/images/${ dibs.path }.png`;
    }
    else
    {
        heroName.textContent = "None";
        heroIcon.src = `/static/images/hero-none.png`;
    }
};

function collectSwapRequests( team, index, player )
{
    let swapRequests = [];
    let hasSwapRequestForClient = false;
    let hasSwapRequestFromClient = false;

    if ( !player )
    {
        return { swapRequests, hasSwapRequestForClient, hasSwapRequestFromClient };
    }

    if ( player.swap_request )
    {
        hasSwapRequestForClient = player.swap_request == clientId;
        if ( hasSwapRequestForClient || isClientObserver() )
        {
            swapRequests.push( index );
        }
    }

    for ( let [ otherIndex, otherPlayer ] of teams[ team ].entries() )
    {
        if ( otherIndex == index )
        {
            continue;
        }

        if ( !otherPlayer )
        {
            continue;
        }

        otherPlayer = players[ otherPlayer ];
        if ( otherPlayer.swap_request == player.id )
        {
            let isSwapRequestFromClient = otherPlayer.id == clientId;
            hasSwapRequestFromClient ||= isSwapRequestFromClient;
            if ( isSwapRequestFromClient || isClientObserver() )
            {
                swapRequests.push( otherIndex );
            }
        }
    }

    return { swapRequests, hasSwapRequestForClient, hasSwapRequestFromClient };
};

function updateSwapRequests( slotDiv, team, index, player )
{
    let { swapRequests, hasSwapRequestForClient, hasSwapRequestFromClient } = collectSwapRequests( team, index, player );

    slotDiv.classList.toggle( "swap-request", swapRequests.length > 0 );
    slotDiv.classList.toggle( "incoming-swap-request", hasSwapRequestForClient );
    slotDiv.classList.toggle( "outgoing-swap-request", hasSwapRequestFromClient );

    for ( let dashIndex = 0; dashIndex < teamSize - 1; ++dashIndex )
    {
        if ( swapRequests.length > dashIndex )
        {
            slotDiv.style.setProperty( `--dash-${ dashIndex }-color`, `var( --${ team }-${ swapRequests[ dashIndex ] }-color )` );
        }
        else
        {
            slotDiv.style.removeProperty( `--dash-${ dashIndex }-color` );
        }
    }
};

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
    let isClient = player.id == clientId;
    if ( isClient )
    {
        playerDiv.classList.add( "client-player" );
    }
    else
    {
        playerDiv.classList.remove( "client-player" );
    }

    playerDiv.classList.remove( ...Array.from( playerDiv.classList ).filter( cls => cls.startsWith( "team-" ) ) );
    playerDiv.classList.add( `team-${ player.team }` );

    let playerName = playerDiv.getElementsByClassName( "players-list-entry-name" )[ 0 ];
    playerName.textContent = player.name;
    let playerIcon = playerDiv.getElementsByClassName( "players-list-entry-icon" )[ 0 ];
    playerIcon.src = `/static/images/${ getTeamIcon( player.team ) }.png`;

    updateTeamSlots( player.team );
    updateHoveredHero();
};

function findHeroIndex( hero )
{
    for ( let [ stat, pool ] of Object.entries( heroes || {} ) )
    {
        if ( !state.stats[ stat ] )
        {
            continue;
        }

        let index = pool.findIndex( ( h ) => h.name == hero );
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
    for ( let [ team, slots ] of Object.entries( teams || {} ) )
    {
        let index = slots.findIndex( ( p ) => p == player );
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
function onUpdateHeroes( newHeroes )
{
    console.log( "updating heroes" );
    heroes = newHeroes;
    for ( let [ stat, pool ] of Object.entries( heroes ) )
    {
        for ( let [ index, hero ] of pool.entries() )
        {
            updateHero( stat, index, hero );
        }
    }
};
socketio.on( "update-heroes", onUpdateHeroes );

function onHeroPicked( hero, isDenied )
{
    let [ stat, index ] = findHeroIndex( hero );
    let heroDiv = document.getElementById( `${ stat }-${ index }` );
    let heroSound = heroDiv.getElementsByClassName( "hero-sound" )[ 0 ];
    playAudioWithDelay( heroSound );

    if ( isDenied )
    {
        playAudioWithDelay( counterPickAudio, 1500 );
    }
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
function onUpdatePlayers( newPlayers )
{
    console.log( "updating all players" );
    players = newPlayers;

    let playerList = document.getElementById( "players-list" );
    playerList.replaceChildren();
    for ( let player of Object.values( players ) )
    {
        let entry = createPlayerEntry( player, "players-list-entry" );
        entry.id = player.id;
        playerList.appendChild( entry );

        updatePlayer( player );
    }
};
socketio.on( "update-players", onUpdatePlayers );

let teams = null;
function onUpdateTeams( newTeams )
{
    console.log( "updating teams" );
    teams = newTeams;
    for ( let team of Object.keys( teams ) )
    {
        updateTeamSlots( team );
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

function escapeHtml( str )
{
    let div = document.createElement( "div" );
    div.textContent = str;
    return div.innerHTML;
};

function localize( key, params = {} )
{
    const recursionLimit = 10;
    let depth = ( params._depth ?? 0 ) + 1;
    if ( depth >= recursionLimit )
    {
        let error = `recursion limit reached in '${ key }'`;
        console.warn( error );
        return localizations.error?.( { error } ) ?? error;
    }

    let localization = localizations[ key ];
    if ( !localization )
    {
        let error = `unknown loc key '${ key }'`;
        console.warn( error );
        return localizations.error?.( { error } ) ?? error;
    }

    return localization( { ...params, _depth: depth } );
};

function onMessage( message )
{
    console.log( "message received" );
    let messageLog = document.getElementById( "message-log" );
    messageLog.innerHTML += `
        <div class="message">
            <span class="message-timestamp">${ getTimestamp() }</span>
            <span class="message-message">${ localize( message.key, message.params ) }</span>
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
