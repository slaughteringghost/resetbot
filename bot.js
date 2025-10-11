const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const express = require('express');

// Configuration
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const PORT = process.env.PORT || 3000;

// Required channels
const REQUIRED_CHANNELS = [
    { 
        id: "-1002628211220", 
        name: "MAIN CHANNEL 📢", 
        link: "https://t.me/c/2628211220/1" 
    },
    { 
        id: "@pytimebruh", 
        name: "BACKUP CHANNEL", 
        link: "https://t.me/pytimebruh" 
    },
];

// Initialize
const bot = new Telegraf(TELEGRAM_TOKEN);
const app = express();

app.use(express.json());

// Membership check function
async function checkMembership(userId, ctx) {
    try {
        const results = await Promise.all(
            REQUIRED_CHANNELS.map(channel => 
                ctx.telegram.getChatMember(channel.id, userId)
                    .then(member => ['member', 'administrator', 'creator'].includes(member.status))
                    .catch(() => false)
            )
        );
        return results.every(status => status);
    } catch (error) {
        return false;
    }
}

// Welcome message
function sendWelcome(ctx) {
    const welcomeText = `
🤖 *Instagram Reset Bot*

*Commands:*
/rst - Single account reset
/blk - Bulk reset (max 5 accounts)

*Developer:* @yaplol

Use the commands below to get started.
    `.trim();
    
    ctx.replyWithMarkdown(welcomeText);
}

// Start command
bot.command('start', async (ctx) => {
    if (ctx.chat.type !== 'private') return;
    
    const isMember = await checkMembership(ctx.from.id, ctx);
    
    if (isMember) {
        sendWelcome(ctx);
    } else {
        const keyboard = Markup.inlineKeyboard([
            ...REQUIRED_CHANNELS.map(ch => [Markup.button.url(ch.name, ch.link)]),
            [Markup.button.callback('✅ Verify Membership', 'verify_join')]
        ]);
        
        ctx.replyWithMarkdown(
            `🔒 *Access Required*\n\nPlease join our channels to use this bot.`,
            keyboard
        );
    }
});

// Verify membership callback
bot.action('verify_join', async (ctx) => {
    await ctx.answerCbQuery();
    const isMember = await checkMembership(ctx.from.id, ctx);
    
    if (isMember) {
        ctx.editMessageText('✅ *Verification Successful!*', { parse_mode: 'Markdown' });
        sendWelcome(ctx);
    } else {
        ctx.answerCbQuery('❌ Please join all channels first', { show_alert: true });
    }
});

// Instagram reset function
async function sendInstagramReset(target) {
    const client = axios.create({ timeout: 10000 });
    
    const methods = [
        // Method 1: Email reset
        async () => {
            try {
                const response = await client.post(
                    'https://www.instagram.com/accounts/account_recovery_send_ajax/',
                    `email_or_username=${target}`,
                    { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
                );
                return response.status === 200 && response.data.includes('email_sent');
            } catch { return false; }
        },
        
        // Method 2: Advanced reset
        async () => {
            try {
                const profile = await client.get(
                    `https://www.instagram.com/api/v1/users/web_profile_info/?username=${target}`,
                    { headers: { 'X-IG-App-ID': '936619743392459' } }
                );
                const userId = profile.data.data.user.id;
                
                const reset = await client.post(
                    'https://i.instagram.com/api/v1/accounts/send_password_reset/',
                    `user_id=${userId}&device_id=${uuidv4()}`,
                    {
                        headers: {
                            'User-Agent': 'Instagram 6.12.1 Android',
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }
                    }
                );
                return reset.data.includes('obfuscated_email');
            } catch { return false; }
        },
        
        // Method 3: Web reset
        async () => {
            try {
                const response = await client.post(
                    'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/',
                    `email_or_username=${target}&flow=fxcal`,
                    {
                        headers: {
                            'x-csrftoken': 'missing',
                            'x-ig-app-id': '936619743392459',
                            'x-requested-with': 'XMLHttpRequest'
                        }
                    }
                );
                return response.data.status === 'ok';
            } catch { return false; }
        }
    ];
    
    const results = await Promise.allSettled(methods.map(method => method()));
    return results.some(result => result.status === 'fulfilled' && result.value);
}

// Single reset command
bot.command('rst', async (ctx) => {
    if (ctx.chat.type !== 'private') return;
    
    const isMember = await checkMembership(ctx.from.id, ctx);
    if (!isMember) {
        return ctx.reply('❌ Please use /start first and join required channels.');
    }
    
    const target = ctx.message.text.split(' ')[1];
    if (!target) {
        return ctx.reply('❌ Usage: /rst username\nExample: /rst example_user');
    }
    
    const msg = await ctx.reply(`⏳ Processing ${target}...`);
    const success = await sendInstagramReset(target);
    
    ctx.telegram.editMessageText(
        msg.chat.id, 
        msg.message_id, 
        null, 
        `${success ? '✅' : '❌'} ${success ? 'Reset sent' : 'Failed'} for ${target}`
    );
});

// Bulk reset command
bot.command('blk', async (ctx) => {
    if (ctx.chat.type !== 'private') return;
    
    const isMember = await checkMembership(ctx.from.id, ctx);
    if (!isMember) {
        return ctx.reply('❌ Please use /start first and join required channels.');
    }
    
    const targets = ctx.message.text.split(' ').slice(1, 6); // Max 5
    if (targets.length === 0) {
        return ctx.reply('❌ Usage: /blk user1 user2 user3\nMax 5 accounts.');
    }
    
    const msg = await ctx.reply(`⏳ Processing ${targets.length} accounts...`);
    
    const results = await Promise.all(
        targets.map(target => sendInstagramReset(target))
    );
    
    const report = ["📊 *Bulk Results:*"];
    targets.forEach((target, i) => {
        report.push(`${results[i] ? '✅' : '❌'} ${target}`);
    });
    
    ctx.telegram.editMessageText(
        msg.chat.id,
        msg.message_id,
        null,
        report.join('\n'),
        { parse_mode: 'Markdown' }
    );
});

// Help command
bot.command('help', async (ctx) => {
    if (ctx.chat.type !== 'private') return;
    
    const isMember = await checkMembership(ctx.from.id, ctx);
    if (!isMember) {
        return ctx.reply('❌ Please use /start first and join required channels.');
    }
    
    ctx.replyWithMarkdown(`
📖 *Command Guide*

*/rst username* - Reset single account
Example: \`/rst example_user\`

*/blk user1 user2* - Reset multiple accounts (max 5)
Example: \`/blk user1 user2 user3\`

*Developer:* @yaplol
    `.trim());
});

// Webhook setup for production
if (process.env.RENDER) {
    const webhookUrl = `https://${process.env.RENDER_EXTERNAL_HOSTNAME}/${TELEGRAM_TOKEN}`;
    bot.telegram.setWebhook(webhookUrl);
    app.use(bot.webhookCallback(`/${TELEGRAM_TOKEN}`));
} else {
    bot.launch();
    console.log('🤖 Bot started in polling mode');
}

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'OK', service: 'Instagram Reset Bot' });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
