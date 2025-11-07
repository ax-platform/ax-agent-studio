/**
 * BASIC TEST: Multi-Agent Message Exchange
 *
 * CRAWL PHASE - Test the absolute basics:
 * - Can Agent A send a message to Agent B?
 * - Can Agent B receive it?
 * - Can Agent B send a message back to Agent A?
 * - Can Agent A receive it?
 *
 * No echo monitors, no queue complexity - just basic message exchange.
 */

import { MCPClientManager } from '@mcpjam/sdk';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Test configuration - using two test agents
const config = {
  'orion_344': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/orion_344',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'rigelz_334': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/rigelz_334',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('BASIC TEST: Multi-Agent Message Exchange');
  console.log('='.repeat(70));
  console.log('Goal: Verify two agents can send messages back and forth');
  console.log('No monitors, no complexity - just basic message exchange\n');
  console.log('='.repeat(70) + '\n');

  // Connect to MCP
  console.log('Step 1: Connecting to agents...');
  const manager = new MCPClientManager(config, {
    defaultClientName: 'Basic Exchange Test',
    defaultClientVersion: '1.0.0'
  });
  console.log('✓ Connected to orion_344 and rigelz_334\n');

  // Test 1: orion_344 → rigelz_334
  console.log('='.repeat(70));
  console.log('TEST 1: orion_344 sends message to rigelz_334');
  console.log('='.repeat(70));

  const message1 = 'Hello rigelz_334! This is a test message from orion_344.';
  console.log(`Sending: "${message1}"`);

  const sendResult1 = await manager.executeTool('orion_344', 'messages', {
    action: 'send',
    content: `@rigelz_334 ${message1}`
  });

  console.log('✓ Message sent\n');

  // Give backend a moment to process
  await sleep(2000);

  // Check if rigelz_334 received it
  console.log('Checking if rigelz_334 received the message...');
  const checkResult1 = await manager.executeTool('rigelz_334', 'messages', {
    action: 'check',
    since: '15m',
    limit: 10,
    mark_read: false  // Don't mark as read, just checking
  });

  // Parse response to find the message
  const messages1 = checkResult1.messages || [];
  const received1 = messages1.find(m =>
    m.sender_name === 'orion_344' &&
    m.content.includes('test message from orion_344')
  );

  if (received1) {
    console.log('✓ TEST 1 PASSED: rigelz_334 received the message');
    console.log(`  Message ID: ${received1.id.substring(0, 8)}`);
    console.log(`  From: ${received1.sender_name}`);
    console.log(`  Content: ${received1.content}\n`);
  } else {
    console.log('✗ TEST 1 FAILED: rigelz_334 did not receive the message');
    console.log(`  Checked ${messages1.length} recent messages, none matched`);
    process.exit(1);
  }

  // Test 2: rigelz_334 → orion_344
  console.log('='.repeat(70));
  console.log('TEST 2: rigelz_334 sends message back to orion_344');
  console.log('='.repeat(70));

  const message2 = 'Hello orion_344! I received your message. Sending a reply back.';
  console.log(`Sending: "${message2}"`);

  const sendResult2 = await manager.executeTool('rigelz_334', 'messages', {
    action: 'send',
    content: `@orion_344 ${message2}`
  });

  console.log('✓ Message sent\n');

  // Give backend a moment to process
  await sleep(2000);

  // Check if orion_344 received it
  console.log('Checking if orion_344 received the reply...');
  const checkResult2 = await manager.executeTool('orion_344', 'messages', {
    action: 'check',
    since: '15m',
    limit: 10,
    mark_read: false  // Don't mark as read, just checking
  });

  // Parse response to find the reply
  const messages2 = checkResult2.messages || [];
  const received2 = messages2.find(m =>
    m.sender_name === 'rigelz_334' &&
    m.content.includes('Sending a reply back')
  );

  if (received2) {
    console.log('✓ TEST 2 PASSED: orion_344 received the reply');
    console.log(`  Message ID: ${received2.id.substring(0, 8)}`);
    console.log(`  From: ${received2.sender_name}`);
    console.log(`  Content: ${received2.content}\n`);
  } else {
    console.log('✗ TEST 2 FAILED: orion_344 did not receive the reply');
    console.log(`  Checked ${messages2.length} recent messages, none matched`);
    process.exit(1);
  }

  // Final summary
  console.log('='.repeat(70));
  console.log('SUMMARY');
  console.log('='.repeat(70));
  console.log('✓ TEST 1 PASSED: orion_344 → rigelz_334 (message delivered)');
  console.log('✓ TEST 2 PASSED: rigelz_334 → orion_344 (reply delivered)');
  console.log('\n🎉 ALL TESTS PASSED - Basic message exchange working!\n');
  console.log('Next steps:');
  console.log('  - Add test for message threading');
  console.log('  - Add test for queue awareness');
  console.log('  - Add test for multi-agent coordination');
  console.log('='.repeat(70) + '\n');

  // Cleanup
  await manager.disconnectServer('orion_344');
  await manager.disconnectServer('rigelz_334');

  process.exit(0);
}

main().catch((error) => {
  console.error('\n✗ Test failed with error:', error.message);
  console.error(error.stack);
  process.exit(1);
});
