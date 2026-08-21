import {test, expect} from 'playwright/test'

const base_url = process.env.BASE_URL;


test('load index page', async ({page}) => {

    await page.goto('/');
    await expect( page.getByRole('heading', {name: 'Ocelot Code Systems'})).toBeVisible()

})

test('load blog page', async ({page}) => {

    await page.goto('/blog');
    await expect( page.getByRole('heading', {name: 'The Dev Blog'})).toBeVisible()

})

test('navigate to blog page', async({page}) => {
    await page.goto('/')
    await page.getByRole('navigation').getByRole('link', { name: 'Blog' }).click()

    await expect( page.getByRole('heading', {name: 'The Dev Blog'})).toBeVisible()

})