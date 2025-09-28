## Minimalist Emacs catsoop Mode

Dependencies:

  1. `markdown-mode` and `multi-mode` from [MELPA Stable](https://stable.melpa.org/)
  2. https://github.com/tarao/multi-mode-util

Once you have the two required packages installed, you can add the following to
your `.emacs` to make a `catsoop-mode` and set it to be the default way to
handle `.catsoop` files:

```
(require 'multi-mode-util)
(defun catsoop-mode ()
  "Treat the current buffer as a catsoop buffer."
  (interactive)
  (markdown-mode)
  (multi-install-chunk-finder
   "<python>[\r\n\t ]" "</python>" 'python-mode)
  (multi-install-chunk-finder
   "<question[^>]*>" "</question>" 'python-mode)
  (multi-install-chunk-finder
   "@{" "}" 'python-mode)
)
(setq auto-mode-alist (cons '("\\.catsoop$" . catsoop-mode)
                       auto-mode-alist))
```

Note that this is quite slow, but it does seem to work, more-or-less.  If
anyone can put together a better one, contributions would be welcome!
