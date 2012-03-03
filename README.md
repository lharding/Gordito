Gordito
=======

An even faster (and possibly easier) Mustache Rendering Tool
------------------------------------------------------------

Gordito is an implementation of a subset of the [Mustache](https://github.com/janl/mustache.js/) templating language. Rather than interpreting templates at runtime, it transpiles your templates to executable Javascript or PHP code for maximum performance.

This should be considered to be a "developer preview" style release - although the API isn't expected to change significantly, only a limited subset of mustache is implemented (although, we find this sufficient to render the new Yahoo! Address Book).

### Is it worth it?

That's up to you. Our own informal tests show about a 10x rendering speedup over interpreted solutions like dust.js or other Mustache renderers, and the JS output is similar in size to the original mustache templates, and can be minified by your minifier. The support code is 2K unminified.

Supported Functionality
-----------------------

*   Variable substitution: {{identifier}} --> Value of context.identifier, same semantics as normal Mustache.
*   Sections: {{#identifier}}Stuff!{{/identifier}} --> Outputs "Stuff!" if context.identifier is truthy, n repetitions of "Stuff!" if context.identifier is a list of length n, etc. Same semantics as normal Mustache.
*   Inverse Sections: {{^identifier}}Stuff!{{/identifier}} --> Outputs "Stuff!" if context.identifier is falsy. Same semantics as normal mustache.
*   Partials: {{> filename}} --> Render "filename.mu" from the working directory. Same semantics as normal mustache.
*   Localization string namespace: Variable substitutions of the form {{str_identifier}} will perform a localization string lookup. See the usage section for details.

Important Unsupported Functionality
-----------------------------------

*   Escaping and unescaping. Data sanitization is up to you. Unlike most mustache renderers, Gordito passes markup and any other data straight through - what you get is the toString() of whatever's in your view object.
*   The triple-mustache {{{no_escape}}} substitution (because of the above).
*   Everything else.

Usage
-----

### Use the Source, Luke!

The documentation below is intended as a rough guide, and should be read alongside the source code of gordito for a full picture.

### Transpiling

To transpile your templates, run the translate_mustache.py script. You will need a makefile or other mechanism to process multiple files as the script operates on one template at a time (with the exception that it will search a specified directory for any necessary partials, and produce a mirroring output directory structure for transpiled partials).

The available options are as follows:

	-f, --f           The mustache template to process
	-r, --rollup      Rollup this template and it's dependencies into a single file.
	-o, --output      The output file of this generated template
	-b, --basepath    Directory in which to search for partials
	-d, --baseoutpath Directory to place output in. Overridden by -o, but not for partials.
	-t, --type        Whether to output Javascript or PHP [must be 'php' or 'js']

Outputting JS creates a YUI module per file. Inspecting the code should make it obvious how to replace this with your favorite flavor of JS module system.

### Rendering

#### Javascript

Use the included gordito.js module to render templates - simply call it's render method with the name of the template you want to render. To use the localization string mechanism, create a hash mapping your localization strings to their values for the current locale, and pass it to TemplateRenderer.setIntlStrings method. For example:

Your JS code:

    //Intl Strings for Klingon/ISO-8859 phoenetic
   	TemplateRenderer.setIntlStrings({
		success: "QAPLA'",
		thanks: "QA TLHO'"
	});
	
	var output = TemplateRenderer.render("it_worked");
	
	//output now contains the rendered template
	
it_worked.mu:

	<h1 style="color: #f00; bgcolor: 000">{{str_success}}</h1>
	{{str_thanks}}
	
#### PHP

Templates are compiled to .inc files named after the input file names. To use, simply include() the relevant template with the correct scope. To set up the scope, the following function may be useful:

    //$filename is the template to render, $ctx is the view object
    public function renderTemplate($filename, $ctx) {
	    $stk = array(); //needed by the generated templates
	    $_TEMPLATE_BASE = self::$TEMPLATES; //directory to find templates in
	
	    include(self::$TEMPLATES.$filename);
    }

Roadmap
-------

*   Finish implementing Mustache featureset (pull requests welcome!)
*   JS DOM API output target for maximum performance in the browser.
*   More languages?
*   Formal performance tests showing exactly how much of a win this thing is.

Legalese
--------
Copyright (c) 2012 Yahoo! Inc.  All rights reserved.  
Copyrights licensed under the MIT License. See the accompanying LICENSE file
for terms.
