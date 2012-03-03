import sys
import os
import re

#Copyright (c) 2012 Yahoo! Inc.  All rights reserved.  
#Copyrights licensed under the MIT License. See the accompanying LICENSE file
#for terms.

# define command line options
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--f", dest="filename", help="The mustache template to process")
parser.add_option("-r", "--rollup", dest="rollup", action="store_true", help="Rollup this template and it's dependencies into a single file.")
parser.add_option("-o", "--output", dest="output", help="The output file of this generated template")
parser.add_option("-b", "--basepath", dest="basepath", help="The base path of the mustache directory")
parser.add_option("-d", "--baseoutpath", dest="baseoutpath", help="Directory to place output in. Overridden by -o, but not for dependencies.")
parser.add_option("-t", "--type", dest="type", help="Whether to output Javascript or PHP")

(options, args) = parser.parse_args()

def js_stomp_filename(fname):
    return re.sub(r'[^a-zA-Z0-9]', '_', fname)

def jsrepl(matchobj): 
    res = matchobj.group(0)
    if res.isspace():
        return ' '
    else:     
        return '\\' + res

def js_escape(str):
    smashspaced = re.sub(r'\s+', ' ', str)
    return '"'+re.sub(r'([\'"])', jsrepl, smashspaced)+'"'

# This is used to concat all simple tokens and strings into one .push() statement
def js_buffer_append_multi(arr):
    return "ob.push(" + ", ".join(arr) + ");\n"

#token types
CONTENT = 1
DEREF = 2
END = 3
NEGATE = 4
INCLUDE = 5
CFGSTRING = 7
VARIABLE = 8

#Dependency list for template being compiled
deps = {}

def token(command, arg):
    return {
           'command': command,
           'arg': arg
           }

def genTokens(template):    
    negation = None
    tokens = []

    start = template.find('{{', 0)
    lastEnd = 0

    ###################
    #Tokenization pass#
    ###################

    #PYTHON SUCKS
    #TODO: some cases of a missing } can cause this to hang.
    #If your build fails because this script got wedged here,
    #look for errors in the template it wass processing when it died.
    while (start) >= 0:
        tokens.append(token(CONTENT, template[lastEnd:start]))
        
        start+=2
        end = template.find('}}', start)
        directive = template[start:end]        
        
        command = directive[0:1]
        name = directive[1:].strip()        
        
        #print "DIR "+directive
        #print "COM "+command
        #print "NAM "+name
        #print "NEG "+str(negation)

        if command=='#':
            tokens.append(token(DEREF, name))
        elif command=='/':
            tokens.append(token(END, None))
        elif command=='>':
            tokens.append(token(INCLUDE, name))
        elif command=='^':
            #print "entering negation"
            #push stack just to maintin consistency with block end code...
            tokens.append(token(NEGATE, name))
        elif command=='=':
            print "Unsupported delimiter change directive encountered. Terminating..."
            exit()        
        elif command=='!':
            #print "COMMENT: " + directive
            a=1
        else:                        
            if command != '{':
                #triple brace means unescape, but we don't handle that right now per ymail behavior                
                name = directive
            else:
                end += 1 #we will have an extra } closing this directive, so consume it
                
            if name.find('str_') == 0:
                tokens.append(token(CFGSTRING, name))
            else:                
                tokens.append(token(VARIABLE, name))                

        lastEnd = end+2
        start = template.find('{{', end+2)
        
    tokens.append(token(CONTENT, template[lastEnd:]))        
    tokens.append(token(END, None))

    return tokens

def compile_template(filename):
    global deps

    templateStripped = []
    try:
        template = open(filename, 'r')
        #mustache delimiters will run together with code if we don't have at least a space between lines.
        templateStripped = [line.strip()+"\n" for line in template]
        #templateStripped = [line for line in template]   
    except:
        print "Could not open "+filename
        return ''
    
    tokens = genTokens("".join(templateStripped))

    ##TODO: make it return local output buffer instead of modifying global one?
    deps = {}
    global options
    
    if options.type and options.type == 'php':
        return compileTokensPHP(tokens)[0]
    else:
        compiled = compileTokensJS(tokens)[0] #this fills in deps
        MODULE_PREFIX = 'mu_'
        depStr = "',\n'".join([MODULE_PREFIX+js_stomp_filename(key) for key in deps.keys()])
        if len(depStr) != 0: depStr = "'"+depStr+"'"    
        
        try:
            idx = filename.index("mustache/")
            idx += 9 # length of 'mustache/'
        except:
            idx = 0
    
        fname = js_stomp_filename(filename[idx:][:-3]) #trim off mustache/ dir and .mu extension
        if options.rollup:
            fname = fname + "_rollup"
    
        res =  ("/* AUTO-GENERATED FILE.  DO NOT EDIT. */\n" +
                "YUI.add('"+MODULE_PREFIX+fname+"',function(Y){\n" +
                "Y.namespace('ui.MuTemplates');\n" +
                "Y.ui.MuTemplates."+fname+" = function(__ctx, __world) {\n" +
                "var ob = __world.outbuffer,"+
                "str=__world.strings,"+
                "handleHash=__world.handleHashsign,\n"+ 
                "templates=__world.templates;\n"+ 
                compiled + "\n}\n" +
                "}, '1.0.0', {requires:["+depStr+"]});")
    
        return res

#returns compiled (string, number of tokens consumed)
def compileTokensJS(tokens):
    global deps
    compiled = ''    
    i = 0
    tempbuffer = []
    
    while i < len(tokens) and tokens[i]['command'] != END:
        #print tokens[i]
        
        command = tokens[i]['command']
        arg = tokens[i]['arg']
        
        res = ('', 1)
        
        if command==DEREF:
            # Flush out the tempbuffer
            if (len(tempbuffer) > 0) :
                compiled += js_buffer_append_multi(tempbuffer)
                tempbuffer = []

            res = compileTokensJS(tokens[i+1:])
            res = ("handleHash(function(__ctx, __world) {\n" + res[0] + "\n}, '" + arg + "', __ctx, __world);", res[1]+1 )                                            
        elif command==INCLUDE:
            # Flush out the tempbuffer
            if (len(tempbuffer) > 0) :
                compiled += js_buffer_append_multi(tempbuffer)
                tempbuffer = []

            if options.rollup:
                basePath = options.basepath
                templateStripped = []
                try:
                    print "Processing partial: " + basePath + arg + ".mu"
                    template = open(basePath + arg + ".mu", 'rU')
                    templateStripped = [line.strip()+"\n" for line in template]
                except:
                    print "Could not open "+ basePath + arg + ".mu"
                    res = ('', 1)

                subtokens = genTokens("".join(templateStripped))
                res = (compileTokensJS(subtokens )[0], 1)
            else:
                deps[arg] = arg
                res = ("templates."+js_stomp_filename(arg)+"(__ctx, __world);\n", 1)
        elif command==NEGATE:
            if (len(tempbuffer) > 0) :
                compiled += js_buffer_append_multi(tempbuffer)
                tempbuffer = []

            res = compileTokensJS(tokens[i+1:])    
            res = ("if(!__ctx['"+arg+"']) {\n" + res[0] + "}\n", res[1]+1)
        elif command==CFGSTRING:
            tempbuffer.append("str('"+arg+"', __ctx, __world)")
        elif command==VARIABLE:
            tempbuffer.append("__ctx['"+arg+"']")
        elif command==CONTENT:
            if arg != "":
                tempbuffer.append(js_escape(arg))
        
        #print res
        
        compiled += res[0]
        i+= res[1]

    # Flush out the tempbuffer
    if (len(tempbuffer) > 0) :
        compiled += js_buffer_append_multi(tempbuffer)
        tempbuffer = []
                
    return (compiled, i+1)

#returns compiled (string, number of tokens consumed)
def compileTokensPHP(tokens):
    global deps
    compiled = ''    
    i = 0
    
    while i < len(tokens) and tokens[i]['command'] != END:
        #print tokens[i]
        
        command = tokens[i]['command']
        arg = tokens[i]['arg']
        
        res = ('', 0)
        
        if command==DEREF:
            res = compileTokensPHP(tokens[i+1:])
            res = ("<?php $_varname = '"+arg+"'; " +
            """
            $_items = array();   
            $_var = $ctx->$_varname;
            $_should_descend_context = !is_scalar($_var);
            if($_var) {                
                if(!is_array($_var)) {
                    $_items[] = $_var;
                }
                else {
                    $_items = $_var;
                }
            }
                
            $stk[] = $ctx;
            foreach($_items as $_ctx_item) {
                if($_should_descend_context) {
                    $ctx = $_ctx_item;
                }
                ?>""" 
                + res[0] + "<?php } $ctx = array_pop($stk); ?>", res[1]+1 )
        elif command==INCLUDE:                        
            if options.rollup:
                basePath = options.basepath
                try:
                    print "Processing partial: " + basePath + arg + ".mu"
                    template = open(basePath + arg + ".mu", 'rU')
                    templateStripped = [line.strip()+"\n" for line in template]
                    
                    subtokens = genTokens("".join(templateStripped))
                    res = (compileTokensPHP(subtokens )[0], 1)
                except:
                    print "Could not open "+ basePath + arg + ".mu"
                    res = ('', 1)
            else:
                #fname = js_stomp_filename(arg)
                deps[arg] = arg
                res = ("<?php include($_TEMPLATE_BASE.'"+arg+".inc'); ?>", 1)
                
        elif command==NEGATE:    
            res = compileTokensPHP(tokens[i+1:])    
            res = ("<?php $_var = '"+arg+"'; if(!isset($ctx->$_var) || empty($ctx->$_var) ) { ?>" + res[0] + "<?php } ?>", res[1]+1)
        elif command==CFGSTRING:
            res = ("<?php echo $this->getIString('"+arg+"', $ctx); ?>", 1)
        elif command==VARIABLE:
            res = ("<?php $_var = '"+arg+"'; echo $ctx->$_var; ?>", 1)
        elif command==CONTENT:
            res = (arg, 1)
        
        #print res
        
        compiled += res[0]
        i+= res[1]
                
    return (compiled, i+1)

            
# setup php path
basename, extension = os.path.splitext(options.filename)

sourcedir = "mustache/"
if options.basepath:
    sourcedir = options.basepath 

destdir = ""
if options.baseoutpath:
    destdir = options.baseoutpath

if options.output:
    newPath = options.output
else:
    if options.type and options.type == 'php':            
        newPath = basename.replace(sourcedir, destdir +"php_translated/") + ".inc"
    else:   
        newPath = basename.replace(sourcedir, destdir + "js_translated/") + ".js"
    
newPathDir = os.path.dirname(newPath)
if not os.path.exists(newPathDir) :
    os.makedirs(newPathDir)
    
if options.rollup:
    basename, extension = os.path.splitext(newPath)
    newPath = basename + "_rollup" + extension

print "Processing "+options.filename+" into "+newPath
#print(compile_template(sys.argv[1]))
    
f = open(newPath, 'w')
f.write(compile_template(options.filename))
f.close()

#if a basepath has been specified, build dependent templates:
if options.basepath and options.baseoutpath:
    print deps
    depstack = deps
    
    while len(depstack) > 0:
        deps = depstack
        depstack = {}    
        
        for key in deps.keys():
            basename = options.basepath + key
            if options.type and options.type == 'php':            
                newPath = basename.replace(options.basepath, options.baseoutpath + "php_translated/") + ".inc"
            else:   
                newPath = basename.replace(options.basepath, options.baseoutpath + "js_translated/") + ".js"
                
            newPathDir = os.path.dirname(newPath)
            if not os.path.exists(newPathDir) :
                os.makedirs(newPathDir)           
            
            print "+  Processing dependency "+key+" into "+newPath
            #print(compile_template(sys.argv[1]))
                
            f = open(newPath, 'w')
            f.write(compile_template(options.basepath + key + ".mu"))
            f.close()
            depstack.update(deps)
elif not options.rollup:
    print "WARNING: not rollup, and no dependencies generated (basepath and baseoutpath must both be specified to generate dependencies)"