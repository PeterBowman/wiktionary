// http://blog.dobryslownik.pl/po-co-przyklady-uzycia-w-slowniku/

var css = [
    '#wikiEditor-ui-examples {display: block; height=10px; background-color: #eeeedd;}',
    '.toggle-button { background-color: white; margin: 5px 0; border: 2px solid #D0D0D0; height: 24px; width: 50px; cursor:pointer; position: relative; display: inline-block; user-select: none; -webkit-user-select: none; -ms-user-select: none; -moz-user-select: none; text-align: center; font-size: large;}',
    '.toggle-button-selected-good { background-color: #83B152; border: 2px solid #7DA652; }',
    '.toggle-button-selected-bad { background-color: #e34a33; border: 2px solid #ca331c; }',
    '.example-div {display: none;}',
    '.example-box {display: inline-block; width:100%;}',
    '.example-buttons {width:60px; float:left; align: center;}',
    '.def-selector {width: 50px; border: solid 2px #eeeedd; align: center; margin: 0 auto}',
    '.raw-text {width:50%; float:left;}',
    '.left-context {font-size: x-small;}',
    '.wikified-text-box {overflow: auto;}',
    '.raw-textarea {resize: vertical;}',
    '.source {font-size: small}',
    '.selector-div-unknown-choice {border: solid 2px red;}',
    '.current {display: block;}'
];


// Make sure the utilities module is loaded (will only load if not already)
mw.loader.using( 'mediawiki.util', function () {

    var config = mw.config.get( [
	'wgPageName',
	'wgAction',
	'wgUserName'
    ] );

var verifyButtonAction = function(content, good_or_bad) {
    return function(event) {
	exampleIndex = $(this).closest('.example-box').attr('data-example-index');

	var $thisbutton = $(this);
	var $thatbutton = $('.current.example-div').find('*[data-example-index=' + exampleIndex + ']').find(':not(.toggle-button.' + good_or_bad + '-button)'); 
	var $selectordiv = $('.current.example-div').find('*[data-example-index=' + exampleIndex + ']').find('.def-selector');

	selectorValue = $selectordiv.find('.num_selector').val();
	if (good_or_bad === 'good' && selectorValue === '') {
    	    $selectordiv.addClass('selector-div-unknown-choice');
	    return -1;
	}

	$selectordiv.removeClass('selector-div-unknown-choice');
	
	$thisbutton.toggleClass('toggle-button-selected-' + good_or_bad);
	$thatbutton.removeClass('toggle-button-selected-' + (good_or_bad === 'good' ? 'bad' : 'good'));
	
	index = $thisbutton.attr('data-index');
	
	if (good_or_bad === 'good') {
	    if (content[index].examples[exampleIndex].good_example === true) {
    	 	content[index].examples[exampleIndex].verificator = 'None';
    	 	content[index].examples[exampleIndex].correct_num = 'None';
    	    }
    	    else if (content[index].examples[exampleIndex].bad_example === true) {
    	 	content[index].examples[exampleIndex].bad_example = false;
    	 	content[index].examples[exampleIndex].correct_num = $('.num_selector').eq(index).find(":selected").text();
    	    }
    	    else {
    	 	content[index].examples[exampleIndex].correct_num = $('.num_selector').eq(index).find(":selected").text();
    	    }
    	    content[index].examples[exampleIndex].good_example = !content[index].examples[exampleIndex].good_example;
    	}
	else if (good_or_bad === 'bad') {
	    if (content[index].examples[exampleIndex].bad_example === true) {
    	 	content[index].examples[exampleIndex].verificator = 'None';
    	 	content[index].examples[exampleIndex].correct_num = 'None';
    	    }
    	    else if (content[index].examples[exampleIndex].good_example === true) {
    	 	content[index].examples[exampleIndex].good_example = false;
    	 	content[index].examples[exampleIndex].correct_num = 'None';
    	    }
       	    content[index].examples[exampleIndex].bad_example = !content[index].examples[exampleIndex].bad_example;
	}

    	content[index].examples[exampleIndex].verificator = config.wgUserName;
	content[index].examples[exampleIndex].example = $('.current.example-div').find('*[data-example-index=' + exampleIndex + ']').find('.raw-textarea').val();
	document.editform.wpTextbox1.value = JSON.stringify(content, null, 4);
	
    };
};
    
    // mw.loader.load( '//rawgit.com/jeresig/jquery.hotkeys/master/jquery.hotkeys.js' );
    /*TODO: <thedj> alkamid: usually, check if the external library is defined if you want to use it, and be prepared for it not being defined and you having to 'reschedule' another attempt to do you 'setup' at a later time, is the strategy often followed in this case.*/

    // Wait for the page to be parsed
    $(document).ready( function () { 


	allowed_prefix = 'Przykła';
	//allowed_prefix = 'Wikisłownik:Dodawanie_przykładów/dane/';

	if (config.wgPageName.indexOf(allowed_prefix) === 0) {
	
	if (config.wgAction === 'view') {
	    //$('#mw-content-text').empty();
	    wikifyExample($('#mw-content-text'), '{{Dodawanie_przykładów_intro}}');
	}

	// This script is intended for pages generated by AlkamidBot only
        if (config.wgAction === 'edit') {


	    //hide textarea
	    $('#wpTextbox1').hide();

	    // add explanatory screenshot at the top
	    $('.wikiEditor-ui-top').prepend('<img id="explain" style="max-width:100%" src="https://upload.wikimedia.org/wikipedia/test/9/92/Przyk%C5%82ad.png" />');
	    
	    // until I find a way to redirect special characters etc. to my custom fields
	    $('#wikiEditor-ui-toolbar').hide();

	    // and a button to hide/show it (and a cookie to control hide/show)
	    $helpbutton = $('<button>')
		.text('pokaż/schowaj pomoc')
		.addClass('help-screenshot-button')
		.click(function() {
		    $('#explain').toggle();
		    
		    if ($.cookie('wiktionary-examples-verification-help') === null) {

			$.cookie( 'wiktionary-examples-verification-help', 1, {
			    expires: 30,
			    path: '/'
			} );
		    }
		    else {
			$.removeCookie('wiktionary-examples-verification-help');
		    }
		    return false;
		})
		.prependTo($('.wikiEditor-ui-top'));

	    if ($.cookie('wiktionary-examples-verification-help') !== null) {
		$('#explain').hide();
	    }
            
	    // Content written by AlkamidBot is in JSON format
            var content = $.parseJSON(document.editform.wpTextbox1.value);
	    
	    // This is the main edit div for usage examples
	    var $editbox = $('<div>')
        	.attr('id', 'wikiEditor-ui-examples')
		.prependTo($('.wikiEditor-ui-bottom'));
            
	    $.each(content, function(index, word) {
		
		// for each word, a div is created - only one is set as "current" at a time,
		// and the other ones are hidden
		$singleExampleDiv = $('<div>')
		    .addClass('example-div')
		    .appendTo($editbox);
		

		// title in bold
		$singleExampleDiv
		    .append($('<p>')
			    .append($('<b>').text(word.title))
			   );
		
		// at the beginning, show only the first word
		if (index === 0) {
		    $singleExampleDiv.addClass('first current');
		}

		// this class is important for deactivating the "next" button
		if (index === content.length -1) {
		    $singleExampleDiv.addClass('last');
		}
		
		// container for definitions
		$defdiv = $('<div>')
		    .addClass('defs-div')
		    .appendTo($singleExampleDiv);
		
		// count meanings (used for dropdown menu later)
		var nums = [];
		var reNums = /\: \(([0-9]\.[0-9]{1,2})\)\s*/g;
		match = reNums.exec(word.definitions);
		while (match !== null) {
		    nums.push(match[1]);
		    match = reNums.exec(word.definitions);
		}
		
		$.each(word.examples, function(ix, example){
		    
		    // containter for example text
		    $textdiv = $('<div>')
			.addClass('example-box')
			.attr('data-example-index', ix)
			.appendTo($singleExampleDiv);

		    // buttons and selector container
		    $buttonsdiv = $('<div>')
			.addClass('example-buttons')
			.appendTo($textdiv);

		    // meaning selector: if words have multiple meanings, one of them must be selected
		    $selectdiv = $('<div>')
			.addClass('def-selector')
			.appendTo($buttonsdiv);

		    $select = $('<select>')
			.addClass('num_selector')
			.appendTo($selectdiv);


		    // add options to select dropdown menu
		    $.each(nums, function(ix, val) {
			$option = $('<option>', {value: val, text: val})
			    .appendTo($select);
			if (example.correct_num !== '' && val === example.correct_num) {
			    $option.attr('selected', 'selected');
			}
		    });

		    // if there's only one meaning, show the selector but don't require the user to select a value
		    if ($select.find('option').length > 1) {
			$select.prepend($('<option>', {value: ''}));
		    }


		    // good/bad example buttons
		    $okbutton = $('<div>')
			.addClass('toggle-button')
			.addClass('good-button')
			.attr('data-index', index)
			.text('✓')
			.appendTo($buttonsdiv);

		    $buttonsdiv.append($('<br/>'));

		    $badbutton = $('<div>')
			.addClass('toggle-button')
			.addClass('bad-button')
			.attr('data-index', index)
			.text('✗')
			.appendTo($buttonsdiv);

		    // if the page has already been edited, select respective buttons
		    if (word.good_example === true) {
			$okbutton.addClass('toggle-button-selected-good');
		    }
		    if (word.bad_example === true) {
			$badbutton.addClass('toggle-button-selected-bad');
		    }
		
		    // container for raw text ([[such]] [[as]] [[this]])
		    $rawTextdiv = $('<div>')
			.addClass('raw-text')
			.appendTo($textdiv);

		    // left context - in case the usage is not clear from what's been copied into the textbox
		    $leftcontext = $('<p>')
			.addClass('left-context')
			.text(example.left_extra)
			.appendTo($rawTextdiv);

		    $wikifiedDiv= $('<div>')
			.addClass('wikified-text-box')
			.appendTo($textdiv);

		    // refresh button - I put it in another diff for it to stay in one place
		    $reloadButton = $('<button>')
			.addClass('refresh-button')
			.text('odśwież')
			.appendTo($wikifiedDiv);

		    $reloadButton.click(function(){
			$div_to_refresh = $(this).closest('.example-box').find('.wikified-text');
			text_to_refresh_from = $(this).closest('.example-box').find('.raw-textarea').val();
			$div_to_refresh.empty();
			wikifyExample($div_to_refresh, text_to_refresh_from, word.title);
			return false;
		    });

		    // wikified text - can be refreshed
		    $wikifiedTextdiv = $('<div>')
			.addClass('wikified-text')
			.attr('data-example-index', ix)
			.appendTo($wikifiedDiv);

		    wikifyExample($wikifiedTextdiv, example.example, word.title);

		    // editable wikitext
		    $rawTextdiv
			.append($('<textarea>')
				.addClass('raw-textarea')
				.text(example.example)
				.attr('rows', 6)
				.attr('data-index', index)
			       );

		    // source of the example
		    $wikifiedDiv
			.append($('<p>')
				.addClass('source')
				.text('źródło: ' + example.source)
			       );


		    $okbutton.click(verifyButtonAction(content, 'good'));
		    $badbutton.click(verifyButtonAction(content, 'bad'));


		if (ix === 0) {
		    $singleExampleDiv.append($('<hr/>'));
		}

		});
		

		wikifyExample($defdiv, word.definitions);

		// leaving for now, need to test speed
		//$.each(word.def_nums, function(def_index, def_value){
		//    $select.append($('<option>', {value: def_value, text: def_value}));
		//});
	
	    });
	    

	    var prevNextButtonAction = function(content, prev_or_next) {
		return function(event) {
		    
		    event.preventDefault();

		    var $text = $('.current.example-div').find('.raw-textarea');
		    var index = $text.attr('data-index');
		    $.each($('.current.example-div').find('.raw-textarea'), function(ix, textarea) {
			content[index].examples[ix].example = textarea.value;
		    });
		    document.editform.wpTextbox1.value = JSON.stringify(content, null, 4);
		    if (!$('.current').hasClass(prev_or_next === 'prev' ? 'first' : 'last')) {
			
			if (prev_or_next === 'prev') {
			    $('.current').hide().removeClass('current')
				.prev().show().addClass('current');
			}
			else if (prev_or_next === 'next') {
			    $('.current').hide().removeClass('current')
				.next().show().addClass('current');
			}
			
			if ($('.current').hasClass(prev_or_next === 'prev' ? 'first' : 'last')) {
			    $('#' + prev_or_next).attr('disabled', true);
			}
			$('#' + (prev_or_next === 'prev' ? 'next' : 'prev')).attr('disabled', null);
		    };
		};
	    };

	    // prev/next buttons taken from http://jsfiddle.net/Qw75j/7/
	    $prevButton = $('<button>')
		.attr('id', 'prev')
		.attr('disabled', 'disabled')
		.text('Poprzedni')
		.click(prevNextButtonAction(content, 'prev'))
		.appendTo($editbox);

	    
	    $nextButton = $('<button>')
		.attr('id', 'next')
		.text('Następny')
		.click(prevNextButtonAction(content, 'next'))
		.appendTo($editbox);

	    if ($('.current').hasClass('last')) {
		$nextButton.attr('disabled', 'disabled');
	    };


        }
	}

	// add keyboard shortcuts for "next", "previous", "good example" and "bad example"
	// $(document).on('keyup', null, 'ctrl+left', prevNextButtonAction('prev'));
	// $(document).on('keyup', null, 'ctrl+right', prevNextButtonAction('next'));
	// $(document).on('keyup', null, 'ctrl+up', verifyButtonAction('good'));
	// $(document).on('keyup', null, 'ctrl+down', verifyButtonAction('bad'));


	mw.util.addCSS( css.join( ' ' ) );
    } );
} );

function wikifyExample($div, exampleText, word) {
    
    word = typeof word !== 'undefined' ? word : 'kdslamsd';
    $.getJSON(
	mw.util.wikiScript( 'api' ),
	
	{'format': 'json',
	 'action': 'parse',
	 'title': word,
	 'text': String(exampleText),
	 'prop': 'text',
	 'disablelimitreport': ''
	}
	
    )
	.done(function(data){
	    $div.append($(data.parse.text['*']));
	});
}
