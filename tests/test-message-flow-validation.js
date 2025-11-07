/**
 * MESSAGE FLOW VALIDATION TEST (CI-friendly)
 *
 * Fast, deterministic test for pre-commit checks.
 * No monitors needed - just validates message delivery and threading.
 *
 * Tests:
 * 1. Basic message exchange (A → B, B → A)
 * 2. Threading (replies reference parent messages)
 * 3. Multi-recipient broadcast (@A @B)
 * 4. Message storm (5 rapid messages, no loss)
 * 5. Queue ordering (messages in chronological order)
 *
 * Expected runtime: <10 seconds
 */

import { MCPClientManager } from '@mcpjam/sdk';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

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
  },
  'lunar_craft_128': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/lunar_craft_128',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

let testsPassed = 0;
let testsFailed = 0;

function assert(condition, testName, errorMsg) {
  if (condition) {
    console.log(`  ✓ ${testName}`);
    testsPassed++;
    return true;
  } else {
    console.log(`  ✗ ${testName}`);
    console.log(`    Error: ${errorMsg}`);
    testsFailed++;
    return false;
  }
}

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('MESSAGE FLOW VALIDATION TEST (CI-friendly)');
  console.log('='.repeat(80));
  console.log('Fast, deterministic test for pre-commit checks');
  console.log('Runtime: <10 seconds\n');
  console.log('='.repeat(80) + '\n');

  const manager = new MCPClientManager(config, {
    defaultClientName: 'Message Flow Validation',
    defaultClientVersion: '1.0.0'
  });

  console.log('✓ Connected to all agents\n');

  try {
    // TEST 1: Basic Message Exchange
    console.log('='.repeat(80));
    console.log('TEST 1: Basic Message Exchange');
    console.log('='.repeat(80));

    const msg1 = 'Hello rigelz_334! This is a test message.';
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: `@rigelz_334 ${msg1}`
    });
    console.log(`Sent: orion_344 → rigelz_334`);

    await sleep(1000);

    const check1 = await manager.executeTool('rigelz_334', 'messages', {
      action: 'check',
      since: '15m',
      limit: 10
    });

    const received1 = (check1.messages || []).find(m =>
      m.sender_name === 'orion_344' &&
      m.content.includes('test message')
    );

    assert(received1, 'Message delivered', 'Message not found');
    assert(received1?.sender_name === 'orion_344', 'Sender correct', `Expected orion_344, got ${received1?.sender_name}`);
    console.log('');

    // TEST 2: Reply with Threading
    console.log('='.repeat(80));
    console.log('TEST 2: Reply with Threading');
    console.log('='.repeat(80));

    const msg2 = 'Reply to your test message!';
    await manager.executeTool('rigelz_334', 'messages', {
      action: 'send',
      content: `@orion_344 ${msg2}`,
      reply_to: received1.id
    });
    console.log(`Sent: rigelz_334 → orion_344 (reply_to: ${received1.id.substring(0, 8)})`);

    await sleep(1000);

    const check2 = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 10
    });

    const reply = (check2.messages || []).find(m =>
      m.sender_name === 'rigelz_334' &&
      m.content.includes('Reply to your test')
    );

    assert(reply, 'Reply delivered', 'Reply not found');
    assert(reply?.parent_message_id === received1.id, 'Threading correct', `Expected parent ${received1.id}, got ${reply?.parent_message_id}`);
    console.log('');

    // TEST 3: Multi-Recipient Broadcast
    console.log('='.repeat(80));
    console.log('TEST 3: Multi-Recipient Broadcast');
    console.log('='.repeat(80));

    const broadcast = '@orion_344 @rigelz_334 Team update: All systems operational';
    await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'send',
      content: broadcast
    });
    console.log(`Sent: lunar_craft_128 → orion_344, rigelz_334`);

    await sleep(1000);

    const checkOrion = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 10
    });

    const checkRigelz = await manager.executeTool('rigelz_334', 'messages', {
      action: 'check',
      since: '15m',
      limit: 10
    });

    const orionGot = (checkOrion.messages || []).find(m =>
      m.sender_name === 'lunar_craft_128' &&
      m.content.includes('systems operational')
    );

    const rigelzGot = (checkRigelz.messages || []).find(m =>
      m.sender_name === 'lunar_craft_128' &&
      m.content.includes('systems operational')
    );

    assert(orionGot, 'orion_344 received broadcast', 'Broadcast not received by orion_344');
    assert(rigelzGot, 'rigelz_334 received broadcast', 'Broadcast not received by rigelz_334');
    assert(orionGot?.id === rigelzGot?.id, 'Same message ID for both', `IDs don't match: ${orionGot?.id} vs ${rigelzGot?.id}`);
    console.log('');

    // TEST 4: Message Storm (No Loss)
    console.log('='.repeat(80));
    console.log('TEST 4: Message Storm (No Loss)');
    console.log('='.repeat(80));

    const stormMessages = [
      'Storm message 1',
      'Storm message 2',
      'Storm message 3',
      'Storm message 4',
      'Storm message 5'
    ];

    console.log('Sending 5 rapid messages...');
    for (let i = 0; i < stormMessages.length; i++) {
      await manager.executeTool('orion_344', 'messages', {
        action: 'send',
        content: `@lunar_craft_128 ${stormMessages[i]}`
      });
      await sleep(200); // Rapid fire
    }
    console.log('Storm sent\n');

    await sleep(1000);

    const stormCheck = await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'check',
      since: '15m',
      limit: 20
    });

    const stormReceived = (stormCheck.messages || []).filter(m =>
      m.sender_name === 'orion_344' &&
      m.content.includes('Storm message')
    );

    assert(stormReceived.length === 5, 'All 5 messages received', `Expected 5, got ${stormReceived.length}`);
    assert(stormReceived.length === 5, 'No message loss', 'Some messages were lost');
    console.log('');

    // TEST 5: Queue Ordering
    console.log('='.repeat(80));
    console.log('TEST 5: Queue Ordering (Chronological)');
    console.log('='.repeat(80));

    const timestamps = stormReceived.map(m => new Date(m.timestamp).getTime());
    const sorted = [...timestamps].sort((a, b) => a - b);
    const isOrdered = JSON.stringify(timestamps) === JSON.stringify(sorted);

    assert(isOrdered, 'Messages in chronological order', 'Messages out of order');

    // Show message order
    console.log('\n  Message order:');
    stormReceived.forEach((m, i) => {
      console.log(`    ${i + 1}. ${m.content.substring(0, 50)}`);
    });
    console.log('');

    // FINAL SUMMARY
    console.log('='.repeat(80));
    console.log('FINAL RESULTS');
    console.log('='.repeat(80));
    console.log(`Tests passed: ${testsPassed}`);
    console.log(`Tests failed: ${testsFailed}`);

    if (testsFailed === 0) {
      console.log('\n🎉 ALL TESTS PASSED - Message flow validated!');
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(0);
    } else {
      console.log(`\n✗ ${testsFailed} TESTS FAILED`);
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(1);
    }

  } catch (error) {
    console.error('\n✗ Test failed with error:', error.message);
    console.error(error.stack);
    await cleanup(manager);
    process.exit(1);
  }
}

async function cleanup(manager) {
  if (manager) {
    await manager.disconnectServer('orion_344');
    await manager.disconnectServer('rigelz_334');
    await manager.disconnectServer('lunar_craft_128');
  }
}

main();
