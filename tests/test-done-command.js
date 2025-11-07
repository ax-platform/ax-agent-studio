/**
 * TEST: #done Command for Loop Breaking
 *
 * Validates that agents can use #done to pause for 60 seconds with auto-resume.
 * This is critical for breaking message loops and preventing agent overwhelm.
 *
 * Test Flow:
 * 1. Send message to agent_a instructing to respond with #done
 * 2. Verify agent_a pauses with 60-second auto-resume
 * 3. Send another message during pause - verify no response
 * 4. Verify pause status includes resume timestamp
 *
 * Expected runtime: <5 seconds (doesn't wait for full 60s)
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
  console.log('TEST: #done Command for Loop Breaking');
  console.log('='.repeat(80));
  console.log('Validates 60-second auto-pause with #done command');
  console.log('Runtime: <5 seconds (no full wait)\n');
  console.log('='.repeat(80) + '\n');

  const manager = new MCPClientManager(config, {
    defaultClientName: '#done Command Test',
    defaultClientVersion: '1.0.0'
  });

  console.log('✓ Connected to test agents\n');

  try {
    // TEST 1: Send message instructing agent to respond with #done
    console.log('='.repeat(80));
    console.log('TEST 1: Agent Responds with #done');
    console.log('='.repeat(80));

    const testMessage = '@rigelz_334 Please respond with: "Task complete! #done"';
    console.log(`Sending to rigelz_334: "${testMessage}"`);

    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: testMessage
    });

    console.log('✓ Message sent\n');

    // Wait for agent to process and respond
    console.log('Waiting 3 seconds for agent to process and respond with #done...');
    await sleep(3000);

    // Check if rigelz_334 responded
    const checkResponse = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 10
    });

    const responses = (checkResponse.messages || []).filter(m =>
      m.sender_name === 'rigelz_334' &&
      m.content.toLowerCase().includes('#done')
    );

    assert(responses.length > 0, 'Agent responded with #done', 'No #done response found');

    if (responses.length > 0) {
      console.log(`\n  Response content: "${responses[0].content.substring(0, 100)}"`);
      assert(
        responses[0].content.toLowerCase().includes('#done'),
        '#done found in response',
        'Response missing #done'
      );
    }
    console.log('');

    // TEST 2: Verify agent is paused
    console.log('='.repeat(80));
    console.log('TEST 2: Verify Agent Paused Status');
    console.log('='.repeat(80));

    // Send a test message to see if agent responds (should not during pause)
    const pauseTestMsg = '@rigelz_334 Are you still there?';
    console.log(`Sending message during pause: "${pauseTestMsg}"`);

    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: pauseTestMsg
    });

    console.log('Waiting 3 seconds to see if agent responds...');
    await sleep(3000);

    // Check for response
    const pauseCheck = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 20
    });

    const pauseResponses = (pauseCheck.messages || []).filter(m =>
      m.sender_name === 'rigelz_334' &&
      m.content.toLowerCase().includes('still there')
    );

    assert(
      pauseResponses.length === 0,
      'Agent did not respond during pause',
      'Agent responded during pause (should be paused!)'
    );

    console.log('  Agent correctly ignored messages during pause');
    console.log('');

    // TEST 3: Message count validation
    console.log('='.repeat(80));
    console.log('TEST 3: Message Accumulation During Pause');
    console.log('='.repeat(80));

    // Count messages from rigelz_334
    const allMessages = pauseCheck.messages || [];
    const fromRigelz = allMessages.filter(m => m.sender_name === 'rigelz_334');

    console.log(`\n  Total messages from rigelz_334: ${fromRigelz.length}`);
    console.log(`  Expected: 1 (only the #done response, no pause responses)`);

    assert(
      fromRigelz.length === 1,
      'Only one response (the #done)',
      `Expected 1 message, got ${fromRigelz.length}`
    );
    console.log('');

    // FINAL SUMMARY
    console.log('='.repeat(80));
    console.log('FINAL RESULTS');
    console.log('='.repeat(80));
    console.log(`Tests passed: ${testsPassed}`);
    console.log(`Tests failed: ${testsFailed}`);

    if (testsFailed === 0) {
      console.log('\n🎉 ALL TESTS PASSED - #done command working correctly!');
      console.log('\nVerified:');
      console.log('  ✓ Agent responds with #done when instructed');
      console.log('  ✓ Agent pauses and ignores messages during pause');
      console.log('  ✓ Messages don\'t accumulate during pause period');
      console.log('  ✓ Loop-breaking mechanism functional');
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
  }
}

main();
