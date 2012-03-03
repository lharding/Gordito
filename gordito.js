/*
Copyright (c) 2012 Yahoo! Inc.  All rights reserved.  
Copyrights licensed under the MIT License. See the accompanying LICENSE file
for terms.
*/

YUI.add('gordito', function(Y){
    var _strings = [];

    function _setIntlStrings(strMap) {
        _strings = strMap;
    }

    function _handleHashsign(__closure, __varname, __ctx, __world) {
        var __var = __ctx[__varname];

        if(__var) {
            if(typeof(__var) !== 'object') {
                __closure(__ctx, __world);
            }
            else if(__var instanceof Array) {
                for (var i = 0; i < __var.length; i++) {
                    __closure(__var[i], __world);
                }
            }
            else {
                __closure(__var, __world);
            }
        }
    }

    function _getString(strname, ctx, world) {
        var str = _strings[strname];

        //Return blank if str is not found.
        if(!str) {
            return "";
        }

        if(str.indexOf("{{") >= 0) {
            var start = 0, res = "", end = 0, name = "";

            while(true) {
                end = str.indexOf("{{", start);
                if(end === -1) {
                    res += str.slice(start, str.length);
                    break;
                }

                res += str.slice(start, end);

                start = str.indexOf("}}", end)+2;

                name = str.slice(end+2, start-2);

                if(name.indexOf("str_") === 0) {
                    res += _strings[name];
                }
                else {
                    res += ctx[name];
                }
            }

            return res;
        }

        return str;
    }

    function _render(templateName, data) {
        var world = {
            ctx : data,
            templates : Y.ui.MuTemplates,
            outbuffer : [],
            strings : _getString,
            handleHashsign: _handleHashsign
        };

        Y.ui.MuTemplates[templateName](data, world);
        return world.outbuffer.join('');
    }

	Y.namespace('tools.gordito');
    Y.tools.gordito.TemplateRenderer = {
        getString: _getString,
        setIntlStrings: _setIntlStrings,
        render: _render
    };

}, '1.0.0',{requires:[]});
