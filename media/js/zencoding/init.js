/**
 * Init Zen Coding module. All MooShell's actions will be namespaced under 
 * 'app_' prefix to prevent possible conflicts with Zen Coding actions
 * @author Sergey Chikuyonok (serge.che@gmail.com)
 * @link http://chikuyonok.ru
 */
(function(){
  var shortcuts = [
    ['Ctrl+Enter', 'Run', 'run'],
    ['Ctrl+Up', 'Switch Previous', 'switchPrev'],
    ['Ctrl+Down', 'Switch Next', 'switchNext'],
    ['Ctrl+Shift+Enter', 'Load Draft', 'loadDraft'],
    ['Ctrl+Shift+Up', 'Toggle Sidebar', 'toggleSidebar'],
    ['Ctrl+Shift+L', 'Show Shortcut dialog', 'showShortcutDialog']
  ];
  
  // register all actions as Zen Coding ones
  var core = zen_editor.getCore(), s;
  for (var i = 0, il = shortcuts.length; i < il; i++) {
    s = shortcuts[i];
    // register mooshell's action as Zen Coding's one
    core.registerAction('app_' + s[2], createBinding(s[2]));
    
    // register keyboard shortcut
    zen_editor.shortcut(s[0], s[1], 'app_' + s[2]);
  }
  
  function createBinding(action_name) {
    return function() {
      console.log(action_name)
      mooshell[action_name].bind(mooshell).call();
    }
  }
})();
