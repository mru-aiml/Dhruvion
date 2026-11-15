const fs = require('fs');
const file = 'D:\\Downloads\\NASA Challenge\\frontend\\src\\features\\science-explorer\\ScienceExplorerPage.tsx';
let content = fs.readFileSync(file, 'utf8');

// Build replacement using explicit character codes for & l t ;
// & = 38, l = 108, t = 116, ; = 59
const ltEntity = String.fromCharCode(38, 108, 116, 59);
const replacement = 'Low (' + ltEntity + ' 0.50)';
console.log('Replacement:', replacement);
for (let i = 0; i < replacement.length; i++) {
  console.log(i, replacement[i], replacement.charCodeAt(i));
}
content = content.replace(/Low \(< 0\.50\)/, replacement);

fs.writeFileSync(file, content, 'utf8');
console.log('Fixed with char codes');