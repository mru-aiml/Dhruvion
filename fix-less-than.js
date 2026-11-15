const fs = require('fs');
const file = 'D:\\Downloads\\NASA Challenge\\frontend\\src\\features\\science-explorer\\ScienceExplorerPage.tsx';
let content = fs.readFileSync(file, 'utf8');

// Use HTML entity < (ampersand-l-t-semicolon)
const replacement = 'Low (< 0.50)';
content = content.replace(/Low \(< 0\.50\)/, replacement);

fs.writeFileSync(file, content, 'utf8');
console.log('Fixed with HTML entity');