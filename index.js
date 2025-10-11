const { Telegraf, Markup, session } = require('telegraf');
const { message } = require('telegraf/filters');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const express = require('express');

// =========================
// Configuration & Constants
// =========================

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const WEBHOOK_URL = process.env.RENDER_EXTERNAL_URL || process.env.WEBHOOK_URL;
const PORT = process.env.PORT || 8000;
const DEV_HANDLE = "@yaplol";

// Channel Configuration
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

// Validation
if (!TELEGRAM_TOKEN) {
    console.error("❌ FATAL: TELEGRAM_BOT_TOKEN environment variable not set");
    process.exit(1);
}

// =========================
// Bot Initialization
// =========================

const bot = new Telegraf(TELEGRAM_TOKEN);
const app = express();

// Middleware Configuration
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Application State Management
const applicationState = {
    initialized: false,
    webhookVerified: false,
    error: null,
    startupTime: new Date().toISOString(),
    statistics: {
        totalRequests: 0,
        successfulResets: 0,
        failedResets: 0
    }
};

// =========================
// Utility Functions
// =========================

/**
 * Membership Verification Service
 */
class MembershipService {
    static async verifyUserMembership(userId, ctx) {
        try {
            const verificationPromises = REQUIRED_CHANNELS.map(channel => 
                this.checkSingleChannel(userId, channel.id, ctx)
            );
            
            const results = await Promise.allSettled(verificationPromises);
            return results.map(result => 
                result.status === 'fulfilled' ? result.value : false
            );
        } catch (error) {
            console.error(`Membership verification failed for user ${userId}:`, error);
            return REQUIRED_CHANNELS.map(() => false);
        }
    }

    static async checkSingleChannel(userId, channelId, ctx) {
        try {
            const member = await ctx.telegram.getChatMember(channelId, userId);
            return ['member', 'administrator', 'creator'].includes(member.status);
        } catch (error) {
            if (error.description?.includes('user not found')) {
                return false;
            }
            console.warn(`Channel check failed for ${channelId}:`, error.message);
            return false;
        }
    }

    static generateVerificationKeyboard() {
        const buttons = REQUIRED_CHANNELS.map(channel => 
            [Markup.button.url(channel.name, channel.link)]
        );
        buttons.push([Markup.button.callback('✅ Verify Membership', 'verify_membership')]);
        
        return Markup.inlineKeyboard(buttons);
    }
}

/**
 * Instagram Reset Service
 */
class InstagramResetService {
    constructor() {
        this.httpClient = axios.create({
            timeout: 15000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        });
    }

    async executeResetMethods(target) {
        const methods = [
            this.methodEmailReset.bind(this),
            this.methodAdvancedReset.bind(this),
            this.methodWebReset.bind(this)
        ];

        try {
            const results = await Promise.allSettled(
                methods.map(method => method(target))
            );
            
            const successful = results.some(result => 
                result.status === 'fulfilled' && result.value === true
            );
            
            this.updateStatistics(successful);
            return successful;
        } catch (error) {
            console.error(`Reset execution error for ${target}:`, error.message);
            this.updateStatistics(false);
            return false;
        }
    }

    async methodEmailReset(target) {
        try {
            const response = await this.httpClient.post(
                'https://www.instagram.com/accounts/account_recovery_send_ajax/',
                `email_or_username=${encodeURIComponent(target)}`,
                { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
            );
            return response.status === 200 && response.data.includes('email_sent');
        } catch {
            return false;
        }
    }

    async methodAdvancedReset(target) {
        try {
            const profileResponse = await this.httpClient.get(
                `https://www.instagram.com/api/v1/users/web_profile_info/?username=${target}`,
                { headers: { 'X-IG-App-ID': '936619743392459' } }
            );
            
            const userId = profileResponse.data.data.user.id;
            const deviceId = uuidv4();
            
            const resetResponse = await this.httpClient.post(
                'https://i.instagram.com/api/v1/accounts/send_password_reset/',
                `user_id=${userId}&device_id=${deviceId}`,
                {
                    headers: {
                        'User-Agent': 'Instagram 6.12.1 Android (30/11; 480dpi; 1080x2004; HONOR; ANY-LX2; HNANY-Q1; qcom; ar_EG_#u-nu-arab)',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                }
            );
            
            return resetResponse.data.includes('obfuscated_email');
        } catch {
            return false;
        }
    }

    async methodWebReset(target) {
        try {
            const response = await this.httpClient.post(
                'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/',
                `email_or_username=${encodeURIComponent(target)}&flow=fxcal`,
                {
                    headers: {
                        'x-csrftoken': 'missing',
                        'x-ig-app-id': '936619743392459',
                        'x-requested-with': 'XMLHttpRequest',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                }
            );
            return response.data.status === 'ok';
        } catch {
            return false;
        }
    }

    updateStatistics(success) {
        applicationState.statistics.totalRequests++;
        if (success) {
            applicationState.statistics.successfulResets++;
        } else {
            applicationState.statistics.failedResets++;
        }
    }
}

// =========================
// Message Handlers
// =========================

/**
 * Welcome Message Handler
 */
async function displayWelcomeMessage(ctx) {
    const welcomeText = `
🤖 *Instagram Reset Bot*

*Commands:*
/rst - Single account reset
/blk - Bulk reset (max 5 accounts)

*Developer:* ${DEV_HANDLE}

Use the commands below to get started.
    `.trim();

    await ctx.replyWithMarkdown(welcomeText);
}

/**
 * Membership Verification Handler
 */
async function handleMembershipVerification(ctx, showStatus = false) {
    try {
        const statuses = await MembershipService.verifyUserMembership(ctx.from.id, ctx);
        const allJoined = statuses.every(status => status);

        if (allJoined) {
            return true;
        }

        let message = `🔒 *Access Required*\n\n`;
        
        if (showStatus) {
            message += `*Membership Status:*\n`;
            REQUIRED_CHANNELS.forEach((channel, index) => {
                const icon = statuses[index] ? '✅' : '❌';
                message += `${icon} ${channel.name}\n`;
            });
            message += `\nPlease join all required channels and verify again.`;
        } else {
            message += `To use this bot, please join our official channels.\n\n`;
            message += `Join all channels below and click *Verify Membership*.`;
        }

        await ctx.replyWithMarkdown(
            message,
            MembershipService.generateVerificationKeyboard()
        );
        return false;

    } catch (error) {
        console.error('Membership verification error:', error);
        await ctx.reply('⚠️ System temporarily unavailable. Please try again shortly.');
        return false;
    }
}

/**
 * Command Handlers
 */
async function handleStartCommand(ctx) {
    if (ctx.chat.type !== 'private') {
        return;
    }

    const isMember = await handleMembershipVerification(ctx, false);
    if (isMember) {
        await displayWelcomeMessage(ctx);
    }
}

async function handleVerificationCallback(ctx) {
    try {
        await ctx.answerCbQuery();
        const isMember = await handleMembershipVerification(ctx, true);
        
        if (isMember) {
            await ctx.editMessageText(
                '✅ *Verification Successful!*\n\nYou can now use all bot features.',
                { parse_mode: 'Markdown' }
            );
            await displayWelcomeMessage(ctx);
        }
    } catch (error) {
        console.error('Verification callback error:', error);
        await ctx.answerCbQuery('❌ Verification failed. Please try again.', { show_alert: true });
    }
}

async function handleHelpCommand(ctx) {
    const helpText = `
📖 *Command Guide*

*/rst username* - Reset single account
Example: \`/rst example_user\`

*/blk user1 user2* - Reset multiple accounts (max 5)
Example: \`/blk user1 user2 user3\`

*Developer:* ${DEV_HANDLE}
    `.trim();

    await ctx.replyWithMarkdown(helpText);
}

/**
 * Reset Command Handlers
 */
async function handleSingleReset(ctx) {
    try {
        const args = ctx.message.text.split(' ').slice(1);
        if (args.length === 0) {
            await ctx.replyWithMarkdown(
                '❌ *Usage:* `
