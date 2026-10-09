import {test,expect} from '@playwright/test';
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
});
