import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
const target=path.resolve('work/static-prefix/tools/clearspace');await fs.mkdir(target,{recursive:true});await fs.cp('dist-sample',target,{recursive:true});
const server=spawn(path.resolve('.venv/Scripts/python.exe'),['-m','http.server','43192','--bind','127.0.0.1','--directory',path.resolve('work/static-prefix')],{windowsHide:true,stdio:'ignore'});
for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:43192/tools/clearspace/')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
const browser=await chromium.launch({channel:'msedge'});const page=await browser.newPage({viewport:{width:1440,height:1000}});const requests=[];const errors=[];
page.on('request',r=>requests.push(r.url()));page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:43192/tools/clearspace/');await page.getByRole('heading',{name:'Your space, understood.'}).waitFor();
 await page.getByRole('button',{name:'Keep',exact:true}).click();await page.getByText('Sample review choice saved for this visit.').waitFor();
 await page.reload();await page.getByRole('heading',{name:'Your space, understood.'}).waitFor();
 await page.screenshot({path:'outputs/screenshots/static-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'outputs/screenshots/static-mobile.png',fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 if(requests.some(u=>!u.startsWith('http://127.0.0.1:43192/tools/clearspace/')))throw Error('Unexpected request outside static prefix');
 if(errors.length)throw Error(errors.join('\n'));
 await fs.writeFile('outputs/static-test.json',JSON.stringify({base:'/tools/clearspace/',refresh:'passed',sampleKeep:'passed',mobileOverflow:false,requests,errors},null,2));
}finally{await browser.close();server.kill()}
