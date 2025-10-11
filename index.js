const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');

// Bot configuration
const BOT_TOKEN = '8342949466:AAHIY_3_pqtFfeMoP4AaWJARkgHb-5snHR8';

const bot = new Telegraf(BOT_TOKEN);

// Instagram reset function with better headers
async function instagramReset(email) {
    try {
        // Random delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
        
        const config = {
            url: 'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/',
            method: 'post',
            headers: {
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': 'csrftoken=' + Math.random().toString(36).substring(2) + '; mid=' + Math.random().toString(36).substring(2),
                'origin': 'https://www.instagram.com',
                'referer': 'https://www.instagram.com/accounts/password/reset/',
                'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
                'x-csrftoken': Math.random().toString(36).substring(2),
                'x-ig-app-id': '1217981644879628',
                'x-requested-with': 'XMLHttpRequest'
            },
            data: `email_or_username=${encodeURIComponent(email)}&flow=fxcal`,
            timeout: 10000
        };

        const response = await axios(config);
        
        // Check if rate limited
        if (response.status === 429) {
            return { error: 'Rate limited by Instagram. Please try again after some time.' };
        }
        
        return response.data;
    } catch (error) {
        if (error.response?.status === 429) {
            return { error: '🚫 Rate Limited: Too many requests. Wait 5-10 minutes.' };
        } else if (error.code === 'ECONNABORTED') {
            return { error: '⏰ Request timeout' };
        } else {
            return { error: error.message };
        }
    }
}

// Start command
bot.start(async (ctx) => {
    const welcomeText = `🤖 *Instagram Reset Bot*

*Commands:*
/rst - Single account reset
/blk - Bulk reset (max 5 accounts)

*Developer:* @yaplol

Use the commands below to get started.`;

    const keyboard = Markup.keyboard([
        ['/rst', '/blk']
    ]).resize();

    await ctx.replyWithMarkdown(welcomeText, keyboard);
});

// Single reset command
bot.command('rst', async (ctx) => {
    await ctx.reply('📧 Send Instagram username or email:', 
        Markup.forceReply().selective()
    );
});

// Bulk reset command  
bot.command('blk', async (ctx) => {
    await ctx.reply('📧 Send usernames/emails (one per line, max 5):',
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
        const accounts = ctx.message.text.split('\n').slice(0, 5).filter(a => a.trim());
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
                if ((i + 1) % 2 === 0 || i === accounts.length - 1) {
                    await ctx.telegram.editMessageText(
                        ctx.chat.id, 
                        msg.message_id, 
                        null, 
                        `🔄 ${i + 1}/${accounts.length} processed...`
                    );
                }
                
                await new Promise(resolve => setTimeout(resolve, 2000));
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
