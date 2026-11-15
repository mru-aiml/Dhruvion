const fs = require('fs');
const file = 'D:\\Downloads\\NASA Challenge\\frontend\\src\\features\\science-explorer\\ScienceExplorerPage.tsx';
let content = fs.readFileSync(file, 'utf8');

// Use explicit HTML entity - write the actual characters & l t ;
const replacement = 'Low (< 0.50)';
content = content.replace(/Low \(< 0\.50\)/, replacement);

fs.writeFileSync(file, content, 'utf8');
console.log('Fixed with explicit HTML entity');