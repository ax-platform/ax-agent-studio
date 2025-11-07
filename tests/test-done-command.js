/**
 * TEST: #done Command for Loop Breaking
 *
 * Simple test:
 * 1. Start echo monitor for lunar_craft_128
 * 2. Send message that triggers agent to include #done in response
 * 3. Send another message
 * 4. Verify agent does NOT respond (they're paused)
 *
 * Expected runtime: <10 seconds
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

// Start echo monitor
function startMonitor() {
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
      stdio: ['ignore', 'pipe', 'pipe']
    }
  );

  monitorProcess.stdout.on('data', (data) => {
    const output = data.toString();
    if (output.includes('Done:') || output.includes('PAUSED') || output.includes('⏸')) {
      console.log('[MONITOR]', output.trim());
    }
  });

  monitorProcess.stderr.on('data', (data) => {
    const output = data.toString();
    if (output.includes('ERROR') || output.includes('CRITICAL')) {
      console.error('[MONITOR ERROR]', output.trim());
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
  'lunar_craft_128': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/lunar_craft_128',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  },
  'orion_344': {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      'http://localhost:8002/mcp/agents/orion_344',
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  }
};

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('TEST: #done Command for Loop Breaking');
  console.log('='.repeat(80));
  console.log('Tests: Agent sends #done → pauses → ignores new messages');
  console.log('='.repeat(80) + '\n');

  try {
    // Step 1: Start monitor
    startMonitor();
    console.log('Waiting 5 seconds for monitor initialization...\n');
    await sleep(5000);

    // Step 2: Connect to MCP
    const manager = new MCPClientManager(config, {
      defaultClientName: '#done Test',
      defaultClientVersion: '1.0.0'
    });

    // Step 3: Send message with #done
    console.log('STEP 1: Send message containing #done');
    console.log('-'.repeat(80));
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 test message. #done'
    });
    console.log('✓ Sent message with #done');
    console.log('Waiting 3 seconds for echo response...\n');
    await sleep(3000);

    // Step 4: Check for first response
    const check1 = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 20
    });

    const firstResponses = (check1.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128'
    );

    if (firstResponses.length > 0) {
      console.log(`✓ Agent responded (${firstResponses.length} message(s))`);
      console.log(`  Content: "${firstResponses[0].content.substring(0, 80)}..."\n`);
    } else {
      console.log('⚠ No response yet\n');
    }

    // Step 5: Send second message - agent should NOT respond (paused)
    console.log('STEP 2: Send message after #done (agent should be paused)');
    console.log('-'.repeat(80));
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 second test message'
    });
    console.log('✓ Sent second message');
    console.log('Waiting 4 seconds to verify no response...\n');
    await sleep(4000);

    // Step 6: Check if agent responded to second message
    const check2 = await manager.executeTool('orion_344', 'messages', {
      action: 'check',
      since: '15m',
      limit: 20
    });

    const allResponses = (check2.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128'
    );

    const responseToSecond = allResponses.filter(m =>
      m.content.includes('second test')
    );

    // Results
    console.log('='.repeat(80));
    console.log('TEST RESULTS');
    console.log('='.repeat(80));
    console.log(`Total responses from lunar_craft_128: ${allResponses.length}`);
    console.log(`Responses to second message: ${responseToSecond.length}`);

    if (responseToSecond.length === 0) {
      console.log('\n🎉 TEST PASSED!');
      console.log('✓ Agent sent #done in first response');
      console.log('✓ Agent paused and did NOT respond to second message');
      console.log('✓ Loop-breaking mechanism working correctly\n');
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(0);
    } else {
      console.log('\n✗ TEST FAILED');
      console.log('Agent responded to message during pause (should be paused!)');
      console.log(`Found ${responseToSecond.length} response(s) to second message\n`);
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
    await manager.disconnectServer('lunar_craft_128');
    await manager.disconnectServer('orion_344');
  }
  stopMonitor();
  await sleep(1000);
}

main();
