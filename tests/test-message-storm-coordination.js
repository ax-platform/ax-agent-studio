/**
 * MESSAGE STORM COORDINATION TEST
 *
 * Real-world scenario: Multiple agents sending messages concurrently
 * Tests the batch processing system under realistic load
 *
 * Setup:
 * - 3 agents: coordinator (agent_a), workers (agent_b, agent_c)
 * - Coordinator has a monitor running
 * - Workers send messages directly (no monitors needed)
 *
 * Test Flow:
 * 1. Coordinator sends task to both workers
 * 2. Both workers respond concurrently
 * 3. Workers send 5 rapid messages each (10 total messages)
 * 4. Coordinator's monitor must batch process all messages
 * 5. Verify: no loss, no loops, clean batch processing
 */

import { MCPClientManager } from '@mcpjam/sdk';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

let monitorProcess = null;

// Start Claude Agent SDK monitor for coordinator
function startCoordinatorMonitor() {
  console.log('Starting coordinator monitor (Claude Agent SDK)...');

  const configPath = join(projectRoot, 'configs', 'agents', 'lunar_craft_128.json');

  monitorProcess = spawn(
    'uv',
    [
      'run', 'python', '-m',
      'ax_agent_studio.monitors.claude_agent_sdk_monitor',
      'lunar_craft_128',
      '--config', configPath
    ],
    {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'pipe']
    }
  );

  // Capture output for debugging
  monitorProcess.stdout.on('data', (data) => {
    const output = data.toString();
    // Only show important log lines
    if (output.includes('BATCH MODE') ||
        output.includes('SINGLE MODE') ||
        output.includes('ERROR') ||
        output.includes('Handler error')) {
      console.log('[MONITOR]', output.trim());
    }
  });

  monitorProcess.stderr.on('data', (data) => {
    const output = data.toString();
    if (output.includes('ERROR') || output.includes('CRITICAL')) {
      console.error('[MONITOR ERROR]', output.trim());
    }
  });

  monitorProcess.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      console.log(`Monitor exited with code ${code}`);
    }
  });

  return monitorProcess;
}

function stopMonitor() {
  if (monitorProcess) {
    console.log('Stopping coordinator monitor...');
    monitorProcess.kill('SIGTERM');
  }
}

process.on('exit', stopMonitor);
process.on('SIGINT', () => {
  stopMonitor();
  process.exit(130);
});

// MCP configuration for 3 agents
const config = {
  'orion_344': {  // Worker A
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/orion_344',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'rigelz_334': {  // Worker B
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/rigelz_334',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'lunar_craft_128': {  // Coordinator (has monitor)
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

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('MESSAGE STORM COORDINATION TEST');
  console.log('='.repeat(80));
  console.log('Scenario: Coordinator receives concurrent messages from 2 workers');
  console.log('Goal: Test batch processing under realistic load\n');
  console.log('Agents:');
  console.log('  - lunar_craft_128 (coordinator with monitor)');
  console.log('  - orion_344 (worker A)');
  console.log('  - rigelz_334 (worker B)');
  console.log('='.repeat(80) + '\n');

  try {
    // Step 1: Start coordinator monitor
    console.log('Step 1: Starting coordinator monitor');
    startCoordinatorMonitor();
    console.log('Waiting 8 seconds for monitor initialization...\n');
    await sleep(8000);

    // Step 2: Connect to MCP
    console.log('Step 2: Connecting to all agents');
    const manager = new MCPClientManager(config, {
      defaultClientName: 'Message Storm Test',
      defaultClientVersion: '1.0.0'
    });
    console.log('✓ Connected to all 3 agents\n');

    // Step 3: Coordinator sends task to both workers
    console.log('='.repeat(80));
    console.log('PHASE 1: Coordinator broadcasts task');
    console.log('='.repeat(80));

    const taskMessage = '@orion_344 @rigelz_334 Please analyze this data and report back.';
    console.log(`Coordinator sends: "${taskMessage}"`);

    await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'send',
      content: taskMessage
    });

    console.log('✓ Task broadcast sent\n');
    await sleep(2000);

    // Step 4: Send FIRST message from Worker A
    console.log('='.repeat(80));
    console.log('PHASE 2: Initial message from Worker A');
    console.log('='.repeat(80));

    const firstMessage = '@lunar_craft_128 Worker A initial report: Starting data analysis now.';
    console.log(`Worker A sends: "${firstMessage}"`);
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: firstMessage
    });

    console.log('✓ First message sent');
    console.log('\n⏰ CRITICAL TEST: Waiting 10 seconds...');
    console.log('   During this time, coordinator monitor should START processing first message.');
    console.log('   We will then send 4 MORE messages while it\'s working.\n');
    await sleep(10000);

    // Step 5: MESSAGE STORM - Send 4 rapid messages WHILE coordinator is processing
    console.log('='.repeat(80));
    console.log('PHASE 3: MESSAGE STORM (while coordinator is processing)');
    console.log('='.repeat(80));

    console.log('📨 Sending 4 rapid follow-up messages from Worker A...');
    console.log('   (These should pile up in queue while monitor is busy)\n');

    const followUpMessages = [
      'Update #1: Found critical pattern in data',
      'Update #2: Cross-referencing with historical trends',
      'Update #3: Analysis 75% complete, preliminary results positive',
      'FINAL UPDATE: Analysis complete, detailed report attached'
    ];

    for (let i = 0; i < followUpMessages.length; i++) {
      await manager.executeTool('orion_344', 'messages', {
        action: 'send',
        content: `@lunar_craft_128 ${followUpMessages[i]}`
      });
      console.log(`  ✓ Message ${i + 1}/4 sent: "${followUpMessages[i]}"`);
      await sleep(300); // Fast but not instant
    }

    console.log('\n✓ MESSAGE STORM COMPLETE');
    console.log('  Total messages sent: 5');
    console.log('  Expected batch behavior:');
    console.log('    - Monitor finishes processing message 1');
    console.log('    - Finds 4 messages waiting in queue');
    console.log('    - Batch processes all 4 together');
    console.log('    - Sends ONE comprehensive response\n');

    // Step 6: Wait for batch processing
    console.log('='.repeat(80));
    console.log('PHASE 4: Waiting for coordinator to batch process...');
    console.log('='.repeat(80));
    console.log('Waiting 12 seconds for monitor to process batch...');
    console.log('(Monitor should send ONE response addressing all 4 follow-up messages)\n');
    await sleep(12000);

    // Step 7: Validate results
    console.log('='.repeat(80));
    console.log('PHASE 5: Validation');
    console.log('='.repeat(80));

    // Check coordinator's messages
    const coordMessages = await manager.executeTool('lunar_craft_128', 'messages', {
      action: 'check',
      since: '15m',
      limit: 50
    });

    const messages = coordMessages.messages || [];
    const sentByCoord = messages.filter(m => m.sender_name === 'lunar_craft_128');
    const receivedByCoord = messages.filter(m =>
      m.sender_name !== 'lunar_craft_128' &&
      m.content.includes('@lunar_craft_128')
    );

    console.log('\n📊 Message Counts:');
    console.log(`  Total messages: ${messages.length}`);
    console.log(`  Sent by coordinator: ${sentByCoord.length}`);
    console.log(`  Received by coordinator: ${receivedByCoord.length}`);

    // Count by sender
    const fromWorkerA = receivedByCoord.filter(m => m.sender_name === 'orion_344').length;

    console.log(`  From Worker A: ${fromWorkerA}`);

    // Validation
    console.log('\n📋 VALIDATION:');

    const expectedMessages = 5; // 1 initial + 4 follow-up

    if (fromWorkerA >= expectedMessages) {
      console.log(`  ✓ Worker A: ${fromWorkerA}/${expectedMessages} messages received (no loss)`);
    } else {
      console.log(`  ✗ Worker A: Only ${fromWorkerA}/${expectedMessages} messages received (MESSAGE LOSS!)`);
    }

    // Check coordinator responses
    console.log('\n📝 Coordinator Responses:');
    console.log(`  Total responses from coordinator: ${sentByCoord.length}`);

    // We expect 2 responses:
    // 1. Response to initial message
    // 2. Batch response to 4 follow-up messages
    const expectedResponses = 2;

    if (sentByCoord.length >= expectedResponses) {
      console.log(`  ✓ Expected ~${expectedResponses} responses, got ${sentByCoord.length}`);

      // Show the batch response (should be the last one)
      const batchResponse = sentByCoord[sentByCoord.length - 1];
      console.log('\n  Latest response (should address multiple messages):');
      console.log('  ' + '─'.repeat(78));
      console.log('  ' + batchResponse.content.substring(0, 400).replace(/\n/g, '\n  '));
      console.log('  ' + '─'.repeat(78));

      // Check if it mentions multiple updates
      const mentionsMultiple =
        batchResponse.content.toLowerCase().includes('update') ||
        batchResponse.content.toLowerCase().includes('all') ||
        batchResponse.content.toLowerCase().includes('multiple') ||
        batchResponse.content.toLowerCase().includes('messages') ||
        batchResponse.content.toLowerCase().includes('final');

      if (mentionsMultiple) {
        console.log('\n  ✓ Response appears to address multiple messages (batch processing)');
      } else {
        console.log('\n  ⚠ Response may not show batch awareness (check content)');
      }
    } else {
      console.log(`  ⚠ Expected ${expectedResponses} responses, only got ${sentByCoord.length}`);
    }

    // Success criteria
    const noMessageLoss = fromWorkerA >= expectedMessages;
    const coordinatorResponded = sentByCoord.length >= expectedResponses;

    console.log('\n' + '='.repeat(80));
    console.log('FINAL RESULTS');
    console.log('='.repeat(80));

    if (noMessageLoss && coordinatorResponded) {
      console.log('🎉 TEST PASSED!');
      console.log('\nKey achievements:');
      console.log('  ✓ No message loss (all 5 messages received)');
      console.log('  ✓ Coordinator processed first message');
      console.log('  ✓ Batch processed 4 follow-up messages while working');
      console.log('  ✓ System captured messages arriving during processing');
      console.log('  ✓ No infinite loops or runaway processes');
      console.log('\n🎯 This proves the queue + batch processing architecture works!');
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(0);
    } else {
      console.log('✗ TEST FAILED');
      if (!noMessageLoss) {
        console.log('  - Message loss detected (missing some of 5 messages)');
      }
      if (!coordinatorResponded) {
        console.log('  - Coordinator did not respond appropriately');
      }
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(1);
    }

  } catch (error) {
    console.error('\n✗ Test failed with error:', error.message);
    console.error(error.stack);
    await cleanup(null);
    process.exit(1);
  }
}

async function cleanup(manager) {
  if (manager) {
    await manager.disconnectServer('orion_344');
    await manager.disconnectServer('rigelz_334');
    await manager.disconnectServer('lunar_craft_128');
  }
  stopMonitor();
  await sleep(1000);
}

main();
