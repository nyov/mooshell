var List = new Class({
	
	initialize: function(){
		this.el = {
			deleteTrigger: $$('.deleteFiddle'),
			fiddleItem: $$('.lfItem')
		};
		this.currentSticky;
		this.setDefaults();
		this.toggleDelete();
	},
	
	setDefaults: function(){
		var self = this;
		
		this.el.deleteTrigger.each(function(trigger){
			trigger.addEvents({
				click: this.fetchConfirmation.bind(this)
			});
		}, this);
	},
	
	fetchConfirmation: function(e){
		e.stop();
		var trigger = $(e.target);
		
		// show the confirmation modal
		new Request.JSON({
			url: trigger.get('href'),
			onComplete: function(shell){
				this.showModal(shell);

				$$('.confirmDelete').addEvents({
					click: function(e){
						e.stop();
						this.deleteShell(shell, trigger);
					}.bind(this)
				});
			}.bind(this)
		}).send();
	},
	
	deleteShell: function(shell, trigger){
		new Request.JSON({
			url: shell.delete_url,
			onComplete: function(shell){
				if (shell.deleted){
					this.currentSticky.hide();
					trigger.getParent('.lfItem').dissolve();
				}
			}.bind(this)
		}).send();
	},
		
	toggleDelete: function(){
		this.el.fiddleItem.each(function(fiddle, idx){
			fiddle.addEvents({
				mouseenter: function(){
					this.el.deleteTrigger[idx].setStyle('display', 'inline');
				}.bind(this),
				mouseleave: function(){
					this.el.deleteTrigger[idx].setStyle('display', 'none');
				}.bind(this)
			});
		}, this);
	},
	
	showModalFx: function(){
		$$('.modalWrap')[0].addClass('show');
	},
	
	showModal: function(shell){
		var html = '<div class="modalWrap modal_confirmation">' +
					'<div class="modalHeading"><h3>Are you certain?</h3><span class="close">Close window</span></div>'+
					'<div class="modalBody">You\'re about to permanently delete <strong>{title}</strong>' + 
					(shell.shells > 1 ? ', and <strong>{shells}</strong> of its revisions.' : '') +
					'<div class="actionsCont"><a href="{delete_url}" class="actionButton submit confirmDelete"><span>Confirm delete</span></a></div>' +
					'</div></div>';

		this.currentSticky = new StickyWin({
			content: html.substitute(shell),
			relativeTo: $(document.body),
			position: 'center',
			edge: 'center',
			closeClassName: 'close',
			draggable: true,
			dragHandleSelector: 'h3',
			closeOnEsc: true,
			destroyOnClose: true,
			allowMultiple: false,
			onDisplay: this.showModalFx
		})
		
		this.currentSticky.show();
	}
	
});

window.addEvent('domready', function(){
	new List();
});