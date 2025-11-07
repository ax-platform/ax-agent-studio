/**
 * TEST: #done Command for Loop Breaking
 *
 * Two-phase test:
 * PHASE 1: Verify agent CAN receive messages (normal operation)
 * PHASE 2: After #done, verify agent CANNOT receive messages (blocking works)
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

function startMonitor() {
  console.log('Starting echo monitor for lunar_craft_128...');
  const configPath = join(projectRoot, 'configs', 'agents', 'lunar_craft_128.json');

  monitorProcess = spawn(
    'uv',
    ['run', 'python', '-m', 'ax_agent_studio.monitors.echo_monitor', 'lunar_craft_128', '--config', configPath],
    { cwd: projectRoot, stdio: ['ignore', 'pipe', 'pipe'] }
  );

  monitorProcess.stdout.on('data', (data) => {
    const output = data.toString();
    if (output.includes('Done:') || output.includes('PAUSED') || output.includes('⏸')) {
      console.log('[MONITOR]', output.trim());
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
process.on('SIGINT', () => { stopMonitor(); process.exit(130); });

const config = {
  'lunar_craft_128': {
    command: 'npx',
    args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/lunar_craft_128',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  },
  'orion_344': {
    command: 'npx',
    args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/orion_344',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  }
};

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('TEST: #done Command for Loop Breaking');
  console.log('='.repeat(80));
  console.log('PHASE 1: Verify normal message delivery works');
  console.log('PHASE 2: Verify #done blocks subsequent messages');
  console.log('='.repeat(80) + '\n');

  try {
    // Setup
    startMonitor();
    console.log('Waiting 5 seconds for monitor initialization...\n');
    await sleep(5000);

    const manager = new MCPClientManager(config, {
      defaultClientName: '#done Test',
      defaultClientVersion: '1.0.0'
    });

    // PHASE 1: Verify normal messaging works
    console.log('='.repeat(80));
    console.log('PHASE 1: Normal Message Delivery');
    console.log('='.repeat(80));
    console.log('Goal: Prove agent CAN receive messages before #done\n');

    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 test message without done'
    });
    console.log('✓ Sent: "test message without done"');
    console.log('Waiting 3 seconds for response...\n');
    await sleep(3000);

    const phase1Check = await manager.executeTool('orion_344', 'messages', {
      action: 'check', since: '15m', limit: 20
    });

    const phase1Responses = (phase1Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128' && m.content.includes('without done')
    );

    if (phase1Responses.length > 0) {
      console.log('✅ PHASE 1 PASSED: Agent CAN receive messages');
      console.log(`   Response: "${phase1Responses[0].content.substring(0, 60)}..."\n`);
    } else {
      console.log('❌ PHASE 1 FAILED: Agent did NOT receive message');
      console.log('   Cannot proceed to Phase 2 - basic messaging broken\n');
      await cleanup(manager);
      process.exit(1);
    }

    // PHASE 2: Send #done and verify blocking
    console.log('='.repeat(80));
    console.log('PHASE 2: #done Blocking Test');
    console.log('='.repeat(80));
    console.log('Goal: Prove agent CANNOT receive messages after #done\n');

    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 message with done. #done'
    });
    console.log('✓ Sent: "message with done. #done"');
    console.log('Waiting 3 seconds for response with #done...\n');
    await sleep(3000);

    // Now send another message - should be blocked
    console.log('Sending second message (should be blocked)...');
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 message after done'
    });
    console.log('✓ Sent: "message after done"');
    console.log('Waiting 4 seconds to verify NO response...\n');
    await sleep(4000);

    // Check results
    const phase2Check = await manager.executeTool('orion_344', 'messages', {
      action: 'check', since: '15m', limit: 30
    });

    const allResponses = (phase2Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128'
    );

    const blockedResponse = allResponses.filter(m =>
      m.content.includes('message after done')
    );

    // Final results
    console.log('='.repeat(80));
    console.log('TEST RESULTS');
    console.log('='.repeat(80));
    console.log(`Total responses from lunar_craft_128: ${allResponses.length}`);
    console.log(`Responses to "message after done": ${blockedResponse.length}\n`);

    if (blockedResponse.length === 0) {
      console.log('🎉 PHASE 2 PASSED: Agent CANNOT receive messages after #done\n');
      console.log('='.repeat(80));
      console.log('FINAL RESULT: ALL TESTS PASSED ✅');
      console.log('='.repeat(80));
      console.log('✓ Phase 1: Normal messaging works');
      console.log('✓ Phase 2: #done blocking works');
      console.log('✓ Loop-breaking mechanism functional\n');
      console.log('='.repeat(80) + '\n');
      await cleanup(manager);
      process.exit(0);
    } else {
      console.log('❌ PHASE 2 FAILED: Agent responded during pause!\n');
      console.log('='.repeat(80));
      console.log('FINAL RESULT: TEST FAILED ✗');
      console.log('='.repeat(80));
      console.log('✓ Phase 1: Normal messaging works');
      console.log('✗ Phase 2: #done blocking FAILED');
      console.log(`   Found ${blockedResponse.length} response(s) when expecting 0\n`);
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
