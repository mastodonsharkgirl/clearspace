import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
const exe=path.resolve(process.argv[2]);const data=path.resolve('work/browser-package-data-'+Date.now());
const root=path.resolve('work/browser-fixture/Downloads');await fs.mkdir(root,{recursive:true});await fs.writeFile(path.join(root,'review-me.zip'),Buffer.alloc(12000,1));
const processHandle=spawn(exe,['--headless','--data',data],{windowsHide:true});
let session;
for(let i=0;i<150;i++){try{session=JSON.parse(await fs.readFile(path.join(data,'session.json'),'utf8'));if((await fetch(session.url.split('/#')[0]+'/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
if(!session)throw Error('No package session');
const browser=await chromium.launch({channel:'msedge'});const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(session.url);await page.getByRole('button',{name:'Choose a folder',exact:true}).click();
 await page.getByLabel('Local folder or drive roots').fill(root);
 await page.getByRole('button',{name:'Start metadata scan',exact:true}).click();
 await page.getByText('Local inventory · Selected scope enumerated').waitFor({timeout:20000});
 await page.getByRole('button',{name:'review-me.zip Downloads to review'}).click();
 await page.getByRole('button',{name:'Keep',exact:true}).click();
 await page.getByText('Review choice saved. Keep choices persist across rescans.').waitFor();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export review plan'}).click();await download;
 await page.getByRole('button',{name:'Re-measure free space'}).click();await page.getByText('Observed net free-space change:',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Explore fictional sample'}).click();
 await page.screenshot({path:'outputs/screenshots/packaged-desktop.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));
 const token=session.url.split('token=')[1];await fetch(session.url.split('/#')[0]+'/api/quit',{method:'POST',headers:{'X-Clearspace-Token':token,'Content-Type':'application/json'},body:'{}'});
 await fs.writeFile('outputs/browser-package-test.json',JSON.stringify({browser:'Microsoft Edge',executable:'extracted ZIP',scan:'passed',keep:'passed',export:'passed',remeasure:'passed',sampleScreenshot:'packaged-desktop.png',pageErrors:errors},null,2));
}finally{await browser.close();if(processHandle.exitCode===null)processHandle.kill()}
