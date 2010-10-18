/*
 Layout using CodeMirror
 */

Element.implement({
	getInnerWidth: function() {
		return this.getSize().x -
				this.getStyle('padding-left').toInt() -
				this.getStyle('padding-right').toInt() -
				this.getStyle('border-left-width').toInt() -
				this.getStyle('border-right-width').toInt();
	},
	getInnerHeight: function() {
		return this.getSize().y -
				this.getStyle('padding-top').toInt() -
				this.getStyle('padding-bottom').toInt() -
				this.getStyle('border-top-width').toInt() -
				this.getStyle('border-bottom-width').toInt();
	}
});

var Layout = {
	editors: $H({}),
    
    reservedKeys: [ // list of [modifier,keycode,callbackname]
      ['ctrlKey', 13, 'run'], ['control', 13, 'run']   // c+ret+run'
    ],

    render: function () {
		// instantiate sidebar
		this.sidebar = new Sidebar({
			DOM: 'sidebar'
		});
		window.addEvents({
          'resize': this.resize.bind(this),
          'keydown': function(keyEvent) {
            if (this.isReservedKey(false, keyEvent)) {
              this.routeReservedKey(keyEvent);
            }
          }.bind(this)
        });
		this.sidebar.addEvents({
			'accordion_resized': this.resize.bind(this)
		});
		// set editor labels
		var result = document.id('result');
		$$('.window_label').setStyle('opacity', 0.8);
		if (result) {
			result.getElement('.window_label').setStyle('opacity', 0.3);
			this.result = result.getElement('iframe');
		}
        // resize
		this.resize(); 
        this.resize.bind(this).delay(20);
        // change behaviour for IE
		if (!Browser.Engine.trident4) {
			this.createDragInstances();
		}
        // send an event
		this.fireEvent('ready');
	},

    routeReservedKey: function(keyEvent) {
      this.reservedKeys.each(function(keyDef){
        if (this.matchKey(keyEvent, keyDef)) {
          mooshell[keyDef.getLast()].bind(mooshell).call();
        }
      }, this);
    },
    
    matchKey: function(keyEvent, keyDef) {
      var pass = true;
      if (keyDef.length > 1) {
        pass = keyEvent[keyDef[0]];
      }
      return pass && (keyDef.contains(keyEvent['keyCode']) || keyDef.contains(keyEvent['code']));
    },

    isReservedKey: function(keyCode, keyEvent) {
      return (this.reservedKeys.some(function(keyDef) {
        return this.matchKey(keyEvent, keyDef)
      }, this));
    },

	findLayoutElements: function() {
		// look up some elements, and cache the findings
		this.content = document.id('content');
		this.columns = this.content.getChildren('.column');
		this.windows = this.content.getElements('.window');
		this.shims = this.content.getElements('.column .shim');
		this.handlers = $H({
			'vertical': this.content.getElementById('handler_vertical'),
			'left': this.columns[0].getElement('.handler_horizontal'),
			'right': this.columns[1].getElement('.handler_horizontal')
		});
	},

	registerEditor: function( editor ) {
		this.editors[editor.options.name] = editor;
		this.resize();
	},

	decodeEditors: function() {
		this.editors.each( function(ed) {
			ed.b64decode();
		});
	},

	updateFromMirror: function() {
		this.editors.each( function(ed) {
			ed.updateFromMirror();
		});
	},

	cleanMirrors: function() {
		this.editors.each( function(ed) {
			ed.clean();
		});
	},

	createDragInstances: function() {
		var onDrag_horizontal = function(h) {
			var windows = h.getParent().getElements('.window');
			var top = (h.getPosition(this.content).y + h.getHeight() / 2) / this.content.getHeight() * 100;
			windows[0].setStyle('height', top + '%');
			windows[1].setStyle('height', 100 - top + '%');
		}.bind(this);

		var onDrag_vertical = function(h) {
			var left = (h.getPosition(this.content).x + h.getWidth() / 2) / this.content.getWidth() * 100;
			this.columns[0].setStyle('width', left + '%');
			this.columns[1].setStyle('width', 100 - left + '%');
		}.bind(this);

		this.handlers.each(function(h) {
			var isHorizontal = h.hasClass('handler_horizontal');
			h.dragInstance = new Drag(h, {
				'modifiers': isHorizontal ? {'x': null, 'y': 'top'} : {'x': 'left', 'y': null},
				'limit': {
					'x': [100, this.content.getWidth() - 100],
					'y': [100, this.content.getHeight() - 100]
				},
				'onBeforeStart': function() { this.shims.show(); }.bind(this),
				'onDrag': isHorizontal ? onDrag_horizontal : onDrag_vertical,
				'onCancel': function() { this.shims.hide(); }.bind(this),
				'onComplete': function() { this.shims.hide(); }.bind(this)
			});
		}, this);

		// Save window sizes to cookie onUnload.
		window.addEvent('unload', function() {
			var sizes = {
				'w': [],
				'h': []
			};
			this.columns.each(function(col, i) {
				var width = col.getStyle('width');
				sizes.w[i] = width.contains('%') ? width : null;
			});
			this.windows.each(function(win, i) {
				var height = win.getStyle('height');
				sizes.h[i] = height.contains('%') ? height : null;
			});
			Cookie.write('window_sizes', JSON.encode(sizes), {'domain': location.host});
		}.bind(this));

		// Read window sizes from cookie.
		this.setWindowSizes();
	},
	setWindowSizes: function(sizes) {
		// sizes === undefined --> read from cookie
		// sizes == null/false --> reset sizes + delete cookie
		// sizes == true       --> use sizes
		if (typeof sizes === 'undefined') {
			var sizes = Cookie.read('window_sizes');
			if (sizes) {
				sizes = JSON.decode(sizes);
			}
		}
		if (sizes) {
			if ($type(sizes.w) === 'array') {
				sizes.w.each(function(width, i) {
					this.columns[i].setStyle('width', width);
				}, this);
			}
			if ($type(sizes.h) == 'array') {
				sizes.h.each(function(height, i) {
					this.windows[i].setStyle('height', height);
				}, this);
			}
		} else {
			this.columns.setStyle('width', null);
			this.windows.setStyle('height', null);
			Cookie.dispose('window_sizes', {'domain': location.host});
		}
		this.resize();
	},
	resize: function(e) {

//		this.editors.each( function(ed) {
//			ed.hide();
//		});
//		if (this.result) {
//			this.result.hide();
//		}

		if (!this.content) {
			this.findLayoutElements();
		}

		var win_size = window.getSize();
		var av_height = win_size.y -
						this.columns[0].getPosition().y +
						this.windows[0].getStyle('top').toInt() +
						this.windows[1].getStyle('bottom').toInt();

		this.content.setStyle('height', av_height);

		// set handler positions
		this.handlers.vertical.setStyle('left', this.windows[0].getCoordinates(this.content).right);
		this.handlers.left.setStyle('top', this.windows[0].getCoordinates(this.content).bottom);
		this.handlers.right.setStyle('top', this.windows[2].getCoordinates(this.content).bottom);

		this.fireEvent('resize');
	}
};
// add events to Layout object
$extend(Layout, new Events());
