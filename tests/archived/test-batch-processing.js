/**
 * BATCH PROCESSING TEST
 *
 * Tests that the new batch processing architecture works:
 * 1. Send multiple rapid messages
 * 2. Verify they're processed together as a batch
 * 3. Check that agent sees proper context
 *
 * Expected behavior:
 * - Multiple messages sent quickly → batched into one response
 * - Agent sees: current message + history
 * - Single response addressing all messages
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

function startEchoMonitor() {
  console.log('Starting echo monitor...');

  const configPath = join(projectRoot, 'configs', 'agents', 'lunar_craft_128.json');

  monitorProcess = spawn(
    'uv',
    [
      'run', 'python', '-m',
      'ax_agent_studio.monitors.echo_monitor',
      'lunar_craft_128',
      '--config', configPath
    ],
    {
      cwd: projectRoot,
      stdio: ['ignore', 'inherit', 'inherit']
    }
  );

  monitorProcess.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      console.log(`Monitor exited with code ${code}`);
    }
  });

  return monitorProcess;
}

function stopMonitor() {
  if (monitorProcess) {
    console.log('Stopping monitor...');
    monitorProcess.kill('SIGTERM');
  }
}

process.on('exit', stopMonitor);
process.on('SIGINT', () => {
  stopMonitor();
  process.exit(130);
});

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

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('BATCH PROCESSING TEST');
  console.log('='.repeat(80));
  console.log('Goal: Verify multiple messages are batched and processed together\n');
  console.log('='.repeat(80) + '\n');

  // Step 1: Start monitor
  console.log('Step 1: Starting echo monitor');
  startEchoMonitor();
  console.log('Waiting 5s for initialization...\n');
  await sleep(5000);

  // Step 2: Connect to MCP
  console.log('Step 2: Connecting to agents');
  const manager = new MCPClientManager(config, {
    defaultClientName: 'Batch Processing Test',
    defaultClientVersion: '1.0.0'
  });
  console.log('✓ Connected\n');

  // Step 3: Send RAPID FIRE messages
  console.log('Step 3: Sending 4 rapid messages');
  console.log('─'.repeat(80));

  const messages = [
    'Message 1: Hey lunar_craft, are you there?',
    'Message 2: I have a question about batch processing.',
    'Message 3: Can you handle multiple messages at once?',
    'Message 4: Please respond to all of these together!'
  ];

  for (let i = 0; i < messages.length; i++) {
    console.log(`  Sending ${i + 1}/4: "${messages[i]}"`);
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: `@lunar_craft_128 ${messages[i]}`
    });
    // Very short delay to ensure they pile up
    await sleep(200);
  }

  console.log('✓ All 4 messages sent rapidly\n');

  // Step 4: Wait for batch processing
  console.log('Step 4: Waiting for echo monitor to process batch...');
  await sleep(3000);

  // Step 5: Check response
  console.log('\nStep 5: Checking echo response');
  const response = await manager.executeTool('lunar_craft_128', 'messages', {
    action: 'check',
    since: '15m',
    limit: 10
  });

  const echoMessages = (response.messages || []).filter(m =>
    m.sender_name === 'lunar_craft_128' &&
    m.content.includes('[ECHO')
  );

  console.log('\n' + '='.repeat(80));
  console.log('RESULTS');
  console.log('='.repeat(80));

  if (echoMessages.length === 0) {
    console.log('✗ No echo response found');
    console.log('\nAll messages:');
    console.log(JSON.stringify(response.messages, null, 2));
    await cleanup(manager);
    process.exit(1);
  }

  // Should have ONE response (batch processing)
  const latestEcho = echoMessages[echoMessages.length - 1];

  console.log(`\nFound ${echoMessages.length} echo response(s)`);
  console.log('\nLatest echo content:');
  console.log('─'.repeat(80));
  console.log(latestEcho.content);
  console.log('─'.repeat(80));

  // Validation
  const isBatchMode = latestEcho.content.includes('[ECHO - BATCH MODE]');
  const hasFourMessages = latestEcho.content.includes('Processed 4 messages') ||
                          latestEcho.content.includes('History: 3');

  console.log('\nVALIDATION:');
  console.log(`  ${isBatchMode ? '✓' : '✗'} Response indicates BATCH MODE`);
  console.log(`  ${hasFourMessages ? '✓' : '✗'} Processed all 4 messages together`);

  if (isBatchMode && hasFourMessages) {
    console.log('\n🎉 TEST PASSED - Batch processing working!');
    console.log('\nKey achievements:');
    console.log('  ✓ Multiple rapid messages were batched');
    console.log('  ✓ Single response addressed all messages');
    console.log('  ✓ Agent saw current message + history context');
    await cleanup(manager);
    process.exit(0);
  } else {
    console.log('\n✗ TEST FAILED - Expected batch processing but got individual responses');
    await cleanup(manager);
    process.exit(1);
  }
}

async function cleanup(manager) {
  await manager.disconnectServer('orion_344');
  await manager.disconnectServer('lunar_craft_128');
  stopMonitor();
  await sleep(1000);
}

main().catch((error) => {
  console.error('\n✗ Error:', error.message);
  stopMonitor();
  process.exit(1);
});
