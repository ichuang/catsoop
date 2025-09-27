" syntax highlighting for catsoop files
" based on https://stackoverflow.com/questions/5176972/trouble-using-vims-syn-include-and-syn-region-to-embed-syntax-highlighting

let b:current_syntax=''
unlet b:current_syntax
runtime! syntax/markdown.vim

let b:current_syntax=''
unlet b:current_syntax
syntax include @Markdown syntax/markdown.vim

let b:current_syntax=''
unlet b:current_syntax
syntax include @Python syntax/python.vim
syntax region pythonCode matchgroup=pythonTag start="<python>" end="</python>" containedin=@Markdown contains=@Python
syntax region pythonCodeQuestion matchgroup=questionTag start="<question [^>]*>" end="</question>" containedin=@Markdown contains=@Python
syntax region pythonShort start="@{" end="}" containedin=@Markdown contains=@Python

let b:current_syntax=''
unlet b:current_syntax
syntax include @TeX syntax/tex.vim
syntax region latexDisplayMath start="\$\$" end="\$\$" keepend containedin=@Markdown contains=@TeX

syntax region catsoopComment start="<comment>" end="</comment>"

hi link catsoopComment Comment
hi link pythonTag htmlTag
hi link questionTag htmlTag
let b:current_syntax = 'catsoop'
