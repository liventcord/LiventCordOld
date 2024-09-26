function reconstructSettings(_isGuildSettings) { //
    const leftBar = getId('settings-leftbar');
    leftBar.innerHTML = '';
    isGuildSettings = _isGuildSettings ;
    if(_isGuildSettings) {
        leftBar.innerHTML = getGuildSettingsHTML();
        selectSettingCategory( Overview );

    } else{ 
        leftBar.innerHTML = getSettingsHtml();
    }

}
function openSettings(isNotLoadingDefault=false) {
    if(!isNotLoadingDefault) {
        reconstructSettings(false);
    }
    disableSnowOnSettingsOpen();
    selectSettingCategory(MyAccount); 

    

    getId('settings-overlay').style.display = 'flex';

    getId('settings-menu').style.animation = 'settings-menu-appear-animation 0.3s forwards';
    isSettingsOpen = true;
    

};