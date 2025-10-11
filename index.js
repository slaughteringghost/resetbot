const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');
const cron = require('node-cron');

// Bot configuration
const BOT_TOKEN = process.env.BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const MAIN_CHANNEL_ID = -1002628211220;
const BACKUP_CHANNEL_USERNAME = 'pytimebruh';

// Initialize bot
const bot = new Telegraf(BOT_TOKEN);

// Instagram API configuration
const instagramConfig = {
    url: 'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/',
    headers: {
        'authority': 'www.instagram.com',
        'method': 'POST',
        'path': '/api/v1/web/accounts/account_recovery_send_ajax/',
        'scheme': 'https',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US;q=0.8,en;q=0.7',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': 'csrftoken=BbJnjd.Jnw20VyXU0qSsHLV; mid=ZpZMygABAAH0176Z6fWvYiNly3y2; ig_did=BBBA0292-07BC-49C8-ACF4-AE242AE19E97; datr=ykyWZhA9CacxerPITDOHV5AE; ig_nrcb=1; dpr=2.75; wd=393x466',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/password/reset/?source=fxcal',
        'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; M2101K786) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': 'BbJnjd.Jnw20VyXU0qSsHLV',
        'x-ig-app-id': '1217981644879628',
        'x-ig-www-claim': '0',
        'x-instagram-ajax': '1015181662',
        'x-requested-with': 'XMLHttpRequest'
    }
};

// Check if user is member of required channels
async function checkMembership(ctx) {
    try {
        const mainChannelStatus = await ctx.telegram.getChatMember(MAIN_CHANNEL_ID, ctx.from.id);
        const backupChannelStatus = await ctx.telegram.getChatMember(`@${BACKUP_CHANNEL_USERNAME}`, ctx.from.id);
        
        return mainChannelStatus.status !== 'left' && backupChannelStatus.status !== 'left';
    } catch (error) {
        console.error('Error checking membership:', error);
        return false;
    }
}

// Instagram reset function
async function instagramReset(email) {
    try {
        const data = new URLSearchParams({
            'email_or_username': email,
            'flow': 'fxcal'
        });

        const response = await axios.post(instagramConfig.url, data, {
            headers: instagramConfig.headers,
            timeout: 10000
        });

        return response.data;
    } catch (error) {
        return { error: error.message };
    }
}

// Welcome message
bot.start(async (ctx) => {
    const isMember = await checkMembership(ctx);
    
    if (!isMember) {
        const keyboard = Markup.inlineKeyboard([
            [Markup.button.url('Main Channel', 'https://t.me/+YEObPfKXsK1hNjU9')],
            [Markup.button.url('Backup Channel', `https://t.me/${BACKUP_CHANNEL_USERNAME}`)],
            [Markup.button.callback('✅ I Have Joined', 'check_join')]
        ]);
        
        return ctx.reply(
            `Welcome to Instagram Reset Bot\n\n` +
            `To use this bot, please join our channels first:\n\n` +
            `• Main Channel: @+YEObPfKXsK1hNjU9\n` +
            `• Backup Channel: @${BACKUP_CHANNEL_USERNAME}\n\n` +
            `After joining, click the button below to verify.`,
            keyboard
        );
    }

    ctx.reply(
        `🔐 Instagram Account Reset Bot\n\n` +
        `Available Commands:\n` +
        `/rst - Reset single account\n` +
        `/blk - Bulk reset accounts\n\n` +
        `Developer: @D8N8D\n` +
        `Channel: @Ergusia`,
        Markup.keyboard([['/rst', '/blk']])
            .resize()
            .oneTime()
    );
});

// Check join callback
bot.action('check_join', async (ctx) => {
    await ctx.answerCbQuery();
    const isMember = await checkMembership(ctx);
    
    if (isMember) {
        await ctx.editMessageText(
            `✅ Verification successful!\n\n` +
            `Now you can use the bot commands:\n` +
            `/rst - Reset single account\n` +
            `/blk - Bulk reset accounts`
        );
    } else {
        await ctx.reply('Please join both channels first and try again.');
    }
});

// Single reset command
bot.command('rst', async (ctx) => {
    const isMember = await checkMembership(ctx);
    
    if (!isMember) {
        return ctx.reply('Please join our channels first to use this bot. Use /start to get channel links.');
    }

    ctx.reply(
        'Please send the Instagram username or email to reset:',
        Markup.forceReply()
    );
});

// Bulk reset command
bot.command('blk', async (ctx) => {
    const isMember = await checkMembership(ctx);
    
    if (!isMember) {
        return ctx.reply('Please join our channels first to use this bot. Use /start to get channel links.');
    }

    ctx.reply(
        'Please send the list of Instagram usernames/emails (one per line):',
        Markup.forceReply()
    );
});

// Handle reply to single reset
bot.on('reply_to_message', async (ctx) => {
    if (ctx.message.reply_to_message.text?.includes('username or email to reset')) {
        const email = ctx.message.text.trim();
        
        if (!email) {
            return ctx.reply('Please provide a valid username or email.');
        }

        const processingMsg = await ctx.reply('🔄 Processing reset request...');
        
        try {
            const result = await instagramReset(email);
            
            let responseText = '';
            if (result.error) {
                responseText = `❌ Error: ${result.error}`;
            } else if (result.status === 'ok') {
                responseText = `✅ Reset email sent successfully to: ${email}`;
            } else {
                responseText = `❌ Failed to send reset email. Response: ${JSON.stringify(result)}`;
            }
            
            await ctx.telegram.editMessageText(
                ctx.chat.id,
                processingMsg.message_id,
                null,
                responseText
            );
        } catch (error) {
            await ctx.telegram.editMessageText(
                ctx.chat.id,
                processingMsg.message_id,
                null,
                `❌ Error occurred: ${error.message}`
            );
        }
    }
});

// Handle reply to bulk reset
bot.on('reply_to_message', async (ctx) => {
    if (ctx.message.reply_to_message.text?.includes('list of Instagram usernames/emails')) {
        const accounts = ctx.message.text.trim().split('\n').filter(acc => acc.trim());
        
        if (accounts.length === 0) {
            return ctx.reply('Please provide at least one username or email.');
        }

        if (accounts.length > 50) {
            return ctx.reply('Maximum 50 accounts allowed for bulk reset.');
        }

        const processingMsg = await ctx.reply(`🔄 Processing ${accounts.length} accounts...`);
        let successCount = 0;
        let failCount = 0;
        let results = [];

        for (let i = 0; i < accounts.length; i++) {
            const account = accounts[i].trim();
            if (!account) continue;

            try {
                const result = await instagramReset(account);
                
                if (result.status === 'ok') {
                    successCount++;
                    results.push(`✅ ${account}`);
                } else {
                    failCount++;
                    results.push(`❌ ${account}`);
                }
                
                // Update progress every 5 accounts
                if ((i + 1) % 5 === 0 || i === accounts.length - 1) {
                    await ctx.telegram.editMessageText(
                        ctx.chat.id,
                        processingMsg.message_id,
                        null,
                        `🔄 Processing... ${i + 1}/${accounts.length}\n` +
                        `✅ Success: ${successCount} | ❌ Failed: ${failCount}`
                    );
                }
                
                // Small delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (error) {
                failCount++;
                results.push(`❌ ${account} - Error: ${error.message}`);
            }
        }

        const resultText = results.slice(0, 20).join('\n'); // Show first 20 results
        const moreText = results.length > 20 ? `\n\n... and ${results.length - 20} more accounts` : '';
        
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            processingMsg.message_id,
            null,
            `📊 Bulk Reset Completed\n\n` +
            `✅ Successful: ${successCount}\n` +
            `❌ Failed: ${failCount}\n\n` +
            `Results:\n${resultText}${moreText}`
        );
    }
});

// Error handling
bot.catch((err, ctx) => {
    console.error(`Error for ${ctx.updateType}:`, err);
    ctx.reply('An error occurred. Please try again later.');
});

// Start bot
bot.launch().then(() => {
    console.log('Instagram Reset Bot is running...');
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
