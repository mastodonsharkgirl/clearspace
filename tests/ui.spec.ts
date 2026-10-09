import {test,expect} from '@playwright/test';
test('local startup is real and picker has visible lifecycle',async({page})=>{
 let picker='idle', requests=0;
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/pick'&&route.request().method()==='POST'){requests++;picker='pending'}
  const payload=path==='/api/config'?{picker:true,drives:['C:\\','D:\\']}:path==='/api/report'?{status:'empty',items:0,roots:[],allocated:'0',logical:'0',reviewable:'0',categories:{}}:path==='/api/entries'?{entries:[],total:0}:path==='/api/browse'?{entries:[],total:0,path:'',parent:null,roots:[]}:path==='/api/pick'?{status:picker,path:'',request_id:1}:null;
  await route.fulfill({json:payload});
 });
 await page.goto('http://127.0.0.1:43191/#token=recovery-test',{waitUntil:'domcontentloaded'});
 await expect(page.getByText('YOUR DEVICE / READ-ONLY')).toBeVisible();
 await expect(page.getByText('FICTIONAL DISK / EXPLORER')).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'Choose exactly what to scan'})).toBeVisible();
 await page.getByRole('button',{name:'Browse for a folder',exact:true}).click();
 await expect(page.getByRole('button',{name:'Waiting for Windows picker…'})).toBeDisabled();
 expect(requests).toBe(1);
 picker='cancelled';
 await expect(page.getByText('Folder selection cancelled. You can browse again or paste a path.')).toBeVisible();
 await page.getByRole('button',{name:'Select drive C:\\',exact:true}).click();
 await expect(page.getByLabel('Local folder or drive roots · one per line',{exact:true})).toHaveValue('C:\\');
});
test('fictional workflow and responsive layout',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:43191');
 await expect(page.getByRole('heading',{name:'Your space, understood.'})).toBeVisible();
 await page.getByRole('button',{name:'Keep',exact:true}).click();
 await expect(page.getByText('Sample review choice saved for this visit.')).toBeVisible();
 await page.getByRole('button',{name:'library.db',exact:false}).click();
 await page.getByRole('button',{name:'Open Installed apps'}).click();
 await expect(page.getByText('Sample handoff: Windows Installed apps.')).toBeVisible();
 await page.getByRole('button',{name:'Archive.zip Cloud / reparse'}).click();
 await expect(page.getByRole('heading',{name:'OneDrive · Free up space'})).toBeVisible();
 await page.screenshot({path:'outputs/screenshots/desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'outputs/screenshots/mobile.png',fullPage:true});
 expect(errors).toEqual([]);
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.keyboard.press('Tab');
 expect(await page.evaluate(()=>document.activeElement?.tagName)).not.toBe('BODY');
 await page.setViewportSize({width:720,height:1000});
 await page.evaluate(()=>document.documentElement.style.fontSize='30px');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});
