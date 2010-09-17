// inject iframe and fire event	
var loadResult = function () {
	$$('#result iframe').each(function(el) { el.destroy(); });
	new Element('iframe', {
		'src': show_src,
		'styles': {
			'height': height - 10
		}
	}).inject($('result'));
	this.removeEvent('click',loadResult);
	window.fireEvent('result_included');
};


Element.implement({
	switchLighter: function(lighter_class) {		
		var resizeLighter = function( light ) {
			// recursive function
			if (light.element) {
				resize_element_counter = 0;
				return light.element.setStyle('height', height);
			}
			if (resize_element_counter++ < 200 ) (function(){
				return resizeLighter(light);
			}).delay(1);
		};
		lighter_class = lighter_class || 'standard';
		// destroy all previous lighters, and create a new one 
		// from the currently selected (but only if it's not the Result tab)
		$$('.'+lighter_class+'Lighter').destroy();
		if (this.get('tag') == 'pre') {
			var light = this.light({flame: lighter_class});
			resizeLighter(light);
			return light;
		}
	}
});

this.switchTab = function(action, index) {
	this.sections.removeClass('active');
	this.sections[index].addClass('active');
	this.actions.getParent().removeClass('active');
	action.getParent().addClass('active');
	this.sections[index].switchLighter();
}


window.addEvents({
	load: function(){
		var window_height = (force_height) ? force_height : window.getSize().y;
		height = window_height - $('head').getSize().y - 20;
		$$('.tCont').setStyle('height', height);
		$('result_trigger').addEvent('click', loadResult);
		$('run').addEvent('click', function() { 
			if (!$('result').hasClass('active')) {
				this.switchTab(
					$('result_trigger'), 
					this.sections.indexOf($('result'))
				);
			}
		}.bind(window));
		$('run').addEvent('click', loadResult);
		$('edit').addEvent('click', function(){
			window.open(shell_edit_url, 'editor');
		});
		this.sections	= $$('#tabs .tCont');
		this.actions	= $$('#actions a');
		
		this.actions.each(function(action, index){
			action.addEvents({
				click: function(e){
					if (e) e.stop();
					this.switchTab(action, index);
				}.bind(this)
			});
		}, this);
		
		if (!this.sections[0].hasClass('result')) this.actions[0].fireEvent('click');
	},
	result_included: function() {
		$('result_trigger').removeEvent('click',loadResult);
		$('run').removeEvent('click',loadResult);
		$('run').addEvent('click', function() {
			$('result').getFirst('iframe').src = show_src;
		});
	}
});
