#!/usr/bin/env node
/**
 * Send burst of messages for FILO batching test
 *
 * Usage: node send_burst_messages.js <target_agent> <sender_agent>
 */

import { MCPClientManager } from '@mcpjam/sdk';

const args = process.argv.slice(2);
const TARGET_AGENT = args[0] || 'ghost_ray_363';
const SENDER_AGENT = args[1] || 'lunar_ray_510';

const TEST_MESSAGES = [
  'Message 1: What is the weather?',
  'Message 2: Never mind the weather, what about sports?',
  'Message 3: Actually, I want to talk about food.',
  'Message 4: On second thought, let\'s discuss technology.',
  'Message 5: Final question - can you summarize our conversation?',
];

const mcpConfig = {
  [SENDER_AGENT]: {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      `http://localhost:8002/mcp/agents/${SENDER_AGENT}`,
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

(async () => {
  try {
    console.log(`Sending ${TEST_MESSAGES.length} messages from ${SENDER_AGENT} to ${TARGET_AGENT}...`);

    const manager = new MCPClientManager(mcpConfig, {
      defaultClientName: 'FILO Batching Test',
      defaultClientVersion: '1.0.0'
    });

    for (let i = 0; i < TEST_MESSAGES.length; i++) {
      const message = TEST_MESSAGES[i];
      const content = `@${TARGET_AGENT} ${message}`;

      await manager.executeTool(SENDER_AGENT, 'messages', {
        action: 'send',
        content: content
      });

      console.log(`  ✓ Sent message ${i + 1}/${TEST_MESSAGES.length}`);

      // Small delay between messages
      if (i < TEST_MESSAGES.length - 1) {
        await new Promise(r => setTimeout(r, 100));
      }
    }

    console.log('All messages sent successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error sending messages:', error.message);
    process.exit(1);
  }
})();
