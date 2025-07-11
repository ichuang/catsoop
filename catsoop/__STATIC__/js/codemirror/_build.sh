#!/bin/bash
npm install
node_modules/.bin/rollup editor.mjs -f iife -n catsoop.codemirror -o codemirror.bundle.js -p @rollup/plugin-node-resolve
node_modules/.bin/uglifyjs --source-map -c -o codemirror.bundle.min.js codemirror.bundle.js
