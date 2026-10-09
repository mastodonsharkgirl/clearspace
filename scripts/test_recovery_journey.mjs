import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const session=JSON.parse(await fs.readFile(process.argv[2]||'work/recovery-finaldata/session.json','utf8'));
const browser=await chromium.launch({channel:'msedge'});const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(session.url);
 if(await page.getByText('FICTIONAL DISK / EXPLORER').count())throw Error('Fictional startup');
 const scope=page.getByRole('textbox',{name:'Local folder or drive roots · one per line',exact:true});
 await scope.fill(path.resolve('work/recovery-native/missing'));
 await page.getByRole('button',{name:'Start metadata scan',exact:true}).click();
 await page.getByRole('alert').waitFor();
 await scope.fill(path.resolve('work/recovery-native/fixture'));
 await page.getByRole('button',{name:'Start metadata scan',exact:true}).click();
 await page.getByText('Local inventory · Selected scope enumerated').waitFor({timeout:20000});
 await page.getByRole('button',{name:'fixture ↗ directory',exact:true}).click();
 await page.getByRole('button',{name:'Large ↗ directory',exact:true}).click();
 await page.getByRole('button',{name:'Nested ↗ directory',exact:true}).click();
 await page.getByRole('button',{name:'demo.bin file',exact:true}).click(); await page.getByRole('heading',{name:'demo.bin',exact:true}).waitFor(); await page.getByRole('button',{name:'Keep',exact:true}).click(); await page.getByText('Review choice saved. Keep choices persist across rescans.').waitFor();
 await page.getByRole('button',{name:'Up one level ↑',exact:true}).click();
 await page.getByRole('button',{name:'Nested ↗ directory',exact:true}).waitFor();
 await page.reload();
 await page.getByText('Local inventory · Selected scope enumerated').waitFor();
 if(await page.getByText('FICTIONAL DISK / EXPLORER').count())throw Error('Fictional reload');
 await page.screenshot({path:'outputs/screenshots/recovery-real-inventory.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Mobile overflow');
 const cancelRoot=path.resolve('work/recovery-native/cancel-fixture');await fs.mkdir(cancelRoot,{recursive:true});
 for(let batch=0;batch<25;batch++)await Promise.all(Array.from({length:100},(_,i)=>fs.writeFile(path.join(cancelRoot,`file-${batch*100+i}.txt`),'synthetic')));
 await page.getByRole('button',{name:/^Choose a folder/}).click();
 await scope.fill(cancelRoot);await page.getByRole('button',{name:'Start metadata scan',exact:true}).click();
 await page.getByRole('button',{name:'Cancel operation',exact:true}).click();
 await page.getByText('Local inventory · Scan cancelled · partial results').waitFor({timeout:20000});
 if(errors.length)throw Error(errors.join('\n'));
 const evidence={realStartup:true,invalidPathVisible:true,typedSyntheticScan:true,folderDrilldown:true,upNavigation:true,reloadRealInventory:true,mobileOverflow:false,fileDetailsAndKeep:true,scanProgressAndCancel:true,nativePickerVerified:false,pageErrors:errors}; await fs.writeFile('outputs/recovery-browser-journey.json',JSON.stringify(evidence,null,2)); console.log(JSON.stringify(evidence));
}finally{await browser.close()}

