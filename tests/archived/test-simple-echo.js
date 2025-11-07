/**
 * Simple Echo Test - One Thing at a Time
 *
 * Tests message board awareness by sending ONE message and checking the response.
 * Clear, focused, easy to validate.
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
  console.log('Starting echo monitor for lunar_craft_128...');

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
      stdio: ['ignore', 'inherit', 'inherit']  // Show all output
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
    console.log('\nStopping monitor...');
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
  console.log('\n' + '='.repeat(60));
  console.log('SIMPLE ECHO TEST - Message Board Awareness');
  console.log('='.repeat(60) + '\n');

  // Step 1: Start monitor
  console.log('STEP 1: Starting echo monitor');
  startEchoMonitor();
  console.log('Waiting 5s for initialization...\n');
  await sleep(5000);

  // Step 2: Initialize MCP
  console.log('STEP 2: Connecting to agents');
  const manager = new MCPClientManager(config, {
    defaultClientName: 'Simple Test',
    defaultClientVersion: '1.0.0'
  });
  console.log('Connected!\n');

  // Step 3: Send ONE message
  console.log('STEP 3: Sending test message');
  console.log('  From: orion_344');
  console.log('  To: lunar_craft_128');
  console.log('  Content: "Hello! Testing queue awareness"');

  await manager.executeTool('orion_344', 'messages', {
    action: 'send',
    content: '@lunar_craft_128 Hello! Testing queue awareness'
  });

  console.log('  ✓ Message sent\n');

  // Step 4: Wait and check response
  console.log('STEP 4: Waiting 3s for echo response...\n');
  await sleep(3000);

  console.log('STEP 5: Checking for response');
  const response = await manager.executeTool('lunar_craft_128', 'messages', {
    action: 'check',
    since: '15m',
    limit: 5
  });

  // Step 6: Show what we got
  console.log('\n' + '='.repeat(60));
  console.log('RESPONSE FROM lunar_craft_128:');
  console.log('='.repeat(60));

  const messages = response.messages || [];
  const echoMessages = messages.filter(m =>
    m.sender_name === 'lunar_craft_128' &&
    m.content.includes('[ECHO]')
  );

  if (echoMessages.length > 0) {
    console.log('\n✅ GOT ECHO RESPONSE:\n');
    console.log(echoMessages[0].content);
    console.log('\n' + '='.repeat(60));

    // Simple validation
    const hasQueueInfo = echoMessages[0].content.includes('Queue depth');
    const hasSenderInfo = echoMessages[0].content.includes('orion_344');

    console.log('\nVALIDATION:');
    console.log(`  ${hasQueueInfo ? '✓' : '✗'} Contains queue depth information`);
    console.log(`  ${hasSenderInfo ? '✓' : '✗'} Identifies sender (orion_344)`);

    if (hasQueueInfo && hasSenderInfo) {
      console.log('\n🎉 TEST PASSED - Queue awareness working!');
    } else {
      console.log('\n❌ TEST FAILED - Missing expected information');
    }
  } else {
    console.log('\n❌ NO ECHO RESPONSE RECEIVED');
    console.log('\nAll messages:');
    console.log(JSON.stringify(messages, null, 2));
  }

  // Cleanup
  await manager.disconnectServer('orion_344');
  await manager.disconnectServer('lunar_craft_128');
  stopMonitor();
  await sleep(1000);

  process.exit(echoMessages.length > 0 ? 0 : 1);
}

main().catch((error) => {
  console.error('\n✗ Error:', error.message);
  stopMonitor();
  process.exit(1);
});
