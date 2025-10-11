const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');

// Bot configuration
const BOT_TOKEN = '8342949466:AAHIY_3_pqtFfeMoP4AaWJARkgHb-5snHR8';
const MAIN_CHANNEL_ID = -1002628211220;
const BACKUP_CHANNEL_USERNAME = 'pytimebruh';

const bot = new Telegraf(BOT_TOKEN);

// Instagram reset function
async function instagramReset(email) {
    try {
        const config = {
            url: 'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/',
            method: 'post',
            headers: {
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': 'csrftoken=BbJnjd.Jnw20VyXU0qSsHLV; mid=ZpZMygABAAH0176Z6fWvYiNly3y2; ig_did=BBBA0292-07BC-49C8-ACF4-AE242AE19E97; datr=ykyWZhA9CacxerPITDOHV5AE; ig_nrcb=1; dpr=2.75; wd=393x466',
                'origin': 'https://www.instagram.com',
                'referer': 'https://www.instagram.com/accounts/password/reset/?source=fxcal',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; M2101K786) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
                'x-csrftoken': 'BbJnjd.Jnw20VyXU0qSsHLV',
                'x-ig-app-id': '1217981644879628'
            },
            data: `email_or_username=${encodeURIComponent(email)}&flow=fxcal`
        };

        const response = await axios(config);
        return response.data;
    } catch (error) {
        return { error: error.message };
    }
}

// Check channel membership
async function checkMembership(ctx) {
    try {
        const mainChannel = await ctx.telegram.getChatMember(MAIN_CHANNEL_ID, ctx.from.id);
        const backupChannel = await ctx.telegram.getChatMember(`@${BACKUP_CHANNEL_USERNAME}`, ctx.from.id);
        
        return mainChannel.status !== 'left' && backupChannel.status !== 'left';
    } catch (error) {
        console.log('Membership check error:', error.message);
        return false;
    }
}

// Start command
bot.start(async (ctx) => {
    const welcomeText = `🤖 *Instagram Reset Bot*

*Commands:*
/rst - Single account reset
/blk - Bulk reset (max 10 accounts)

*Developer:* @yaplol
*Channel:* @pytimebruh

Join our channels to use the bot:`;

    const keyboard = Markup.inlineKeyboard([
        [Markup.button.url('📢 Main Channel', 'https://t.me/+YEObPfKXsK1hNjU9')],
        [Markup.button.url('🔔 Backup Channel', `https://t.me/${BACKUP_CHANNEL_USERNAME}`)],
        [Markup.button.callback('✅ Verify Join', 'verify_join')]
    ]);

    await ctx.replyWithMarkdown(welcomeText, keyboard);
});

// Verify join callback
bot.action('verify_join', async (ctx) => {
    await ctx.answerCbQuery();
    const isMember = await checkMembership(ctx);
    
    if (isMember) {
        await ctx.editMessageText(`✅ *Verified!*\n\nYou can now use:\n/rst - Single reset\n/blk - Bulk reset`, {
            parse_mode: 'Markdown',
            ...Markup.inlineKeyboard([
                [Markup.button.callback('🔄 Refresh', 'verify_join')]
            ])
        });
    } else {
        await ctx.answerCbQuery('❌ Please join both channels first', { show_alert: true });
    }
});

// Single reset command
bot.command('rst', async (ctx) => {
    const isMember = await checkMembership(ctx);
    if (!isMember) {
        return ctx.reply('❌ Please join our channels first and use /start');
    }

    await ctx.reply('📧 Send Instagram username or email:', 
        Markup.forceReply().selective()
    );
});

// Bulk reset command  
bot.command('blk', async (ctx) => {
    const isMember = await checkMembership(ctx);
    if (!isMember) {
        return ctx.reply('❌ Please join our channels first and use /start');
    }

    await ctx.reply('📧 Send usernames/emails (one per line, max 10):',
        Markup.forceReply().selective()
    );
});

// Handle replies
bot.on('message', async (ctx) => {
    if (!ctx.message.reply_to_message) return;

    const replyText = ctx.message.reply_to_message.text;
    
    if (replyText.includes('Send Instagram username or email')) {
        // Single reset
        const email = ctx.message.text.trim();
        if (!email) return ctx.reply('❌ Please provide username/email');

        const msg = await ctx.reply('🔄 Processing...');
        
        try {
            const result = await instagramReset(email);
            let response = `📧 *Account:* ${email}\n`;
            
            if (result.status === 'ok') {
                response += '✅ *Status:* Reset email sent';
            } else if (result.error) {
                response += `❌ *Error:* ${result.error}`;
            } else {
                response += `❌ *Failed:* ${JSON.stringify(result)}`;
            }
            
            await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, response, { parse_mode: 'Markdown' });
        } catch (error) {
            await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `❌ Error: ${error.message}`);
        }
    }
    
    else if (replyText.includes('Send usernames/emails')) {
        // Bulk reset
        const accounts = ctx.message.text.split('\n').slice(0, 10).filter(a => a.trim());
        if (accounts.length === 0) return ctx.reply('❌ No valid accounts provided');

        const msg = await ctx.reply(`🔄 Processing ${accounts.length} accounts...`);
        let results = [];

        for (let i = 0; i < accounts.length; i++) {
            const account = accounts[i].trim();
            try {
                const result = await instagramReset(account);
                if (result.status === 'ok') {
                    results.push(`✅ ${account}`);
                } else {
                    results.push(`❌ ${account}`);
                }
                
                // Update progress
                if ((i + 1) % 3 === 0 || i === accounts.length - 1) {
                    await ctx.telegram.editMessageText(
                        ctx.chat.id, 
                        msg.message_id, 
                        null, 
                        `🔄 ${i + 1}/${accounts.length} processed...`
                    );
                }
                
                await new Promise(resolve => setTimeout(resolve, 1500));
            } catch (error) {
                results.push(`❌ ${account} (Error)`);
            }
        }

        const resultText = `📊 *Bulk Reset Complete*\n\n${results.join('\n')}`;
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, resultText, { parse_mode: 'Markdown' });
    }
});

// Error handling
bot.catch((err, ctx) => {
    console.error('Bot error:', err);
});

// Start bot
bot.launch().then(() => {
    console.log('🚀 Instagram Reset Bot started successfully!');
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
