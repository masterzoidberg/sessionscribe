import { test, expect } from '@playwright/test';

test.describe('SessionScribe E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Start the application
    await page.goto('http://localhost:3000');
    await expect(page.locator('h1')).toContainText('SessionScribe');
  });

  test('hotkeys for record start/stop work', async ({ page }) => {
    // Navigate to Record tab
    await page.click('button:has-text("Record")');
    
    // Check initial state - should show Start Recording button
    await expect(page.locator('button:has-text("Start Recording")')).toBeVisible();
    
    // Test Ctrl+Alt+R to start recording
    await page.keyboard.press('Control+Alt+r');
    
    // Should now show Stop and Pause buttons
    await expect(page.locator('button:has-text("Stop")')).toBeVisible();
    await expect(page.locator('button:has-text("Pause")')).toBeVisible();
    
    // Test Ctrl+Alt+R to stop recording
    await page.keyboard.press('Control+Alt+r');
    
    // Should return to Start Recording button
    await expect(page.locator('button:has-text("Start Recording")')).toBeVisible();
  });

  test('hotkey for marking time works', async ({ page }) => {
    // Navigate to Record tab
    await page.click('button:has-text("Record")');
    
    // Start recording first
    await page.click('button:has-text("Start Recording")');
    
    // Test Ctrl+Alt+M for marking
    // This should not cause any errors (check console)
    await page.keyboard.press('Control+Alt+m');
    
    // Should still be in recording state
    await expect(page.locator('button:has-text("Stop")')).toBeVisible();
  });

  test('PHI review workflow', async ({ page }) => {
    // Navigate to Review tab
    await page.click('button:has-text("Review")');
    
    // Should show PHI Review interface
    await expect(page.locator('h2:has-text("PHI Review")')).toBeVisible();
    
    // Check for key elements
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
    
    // Test filter controls
    const filterSelect = page.locator('select');
    if (await filterSelect.isVisible()) {
      await filterSelect.selectOption('ALL');
      await expect(filterSelect).toHaveValue('ALL');
    }
    
    // Test accept/reject all buttons
    const acceptAllBtn = page.locator('button:has-text("Accept All")');
    const rejectAllBtn = page.locator('button:has-text("Reject All")');
    
    if (await acceptAllBtn.isVisible()) {
      await acceptAllBtn.click();
    }
    
    if (await rejectAllBtn.isVisible()) {
      await rejectAllBtn.click();
    }
  });

  test('note generation workflow', async ({ page }) => {
    // Navigate to Note tab
    await page.click('button:has-text("Note")');
    
    // Should show Session Setup wizard
    await expect(page.locator('h2:has-text("Session Setup")')).toBeVisible();
    
    // Test session type selection
    await page.click('text=Individual Therapy');
    await expect(page.locator('[class*="border-blue-500"]')).toBeVisible();
    
    // Test next button
    const nextBtn = page.locator('button:has-text("Next")');
    if (await nextBtn.isVisible() && await nextBtn.isEnabled()) {
      await nextBtn.click();
    }
    
    // Should show prompt template selection
    await expect(page.locator('h3:has-text("Choose Note Template")')).toBeVisible();
    
    // Test template selection
    const defaultTemplate = page.locator('label:has-text("Default DAP Template")');
    if (await defaultTemplate.isVisible()) {
      await defaultTemplate.click();
    }
    
    // Right panel should show note generation area
    await expect(page.locator('h2:has-text("DAP Note Generation")')).toBeVisible();
    
    // Test generate note button
    const generateBtn = page.locator('button:has-text("Generate Note")');
    await expect(generateBtn).toBeVisible();
    
    // Button might be disabled if no redacted text available
    if (await generateBtn.isEnabled()) {
      await generateBtn.click();
      await expect(page.locator('text=Generating...')).toBeVisible();
    }
  });

  test('dashboard offline mode blocks sending', async ({ page }) => {
    // Navigate to Dashboard tab
    await page.click('button:has-text("Dashboard")');
    
    // Should show Live Dashboard
    await expect(page.locator('h2:has-text("Live Dashboard")')).toBeVisible();
    
    // Check for insights selection checkboxes
    const insightCheckboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await insightCheckboxes.count();
    
    if (checkboxCount > 0) {
      // Select some insights
      await insightCheckboxes.first().check();
      await expect(insightCheckboxes.first()).toBeChecked();
    }
    
    // Check send button state
    const sendBtn = page.locator('button:has-text("Confirm & Send")');
    await expect(sendBtn).toBeVisible();
    
    // In offline mode (default), button should be disabled
    // Check status message
    const statusText = page.locator('text*=offline');
    if (await statusText.isVisible()) {
      await expect(sendBtn).toBeDisabled();
    }
  });

  test('navigation between tabs works correctly', async ({ page }) => {
    // Test navigation through all tabs
    const tabs = ['Record', 'Review', 'Note', 'Dashboard'];
    
    for (const tab of tabs) {
      await page.click(`button:has-text("${tab}")`);
      
      // Check that the tab is active (has blue background)
      const activeTab = page.locator(`button:has-text("${tab}")`);
      await expect(activeTab).toHaveClass(/bg-blue-500/);
      
      // Wait a bit for content to load
      await page.waitForTimeout(100);
    }
  });

  test('audio device selection works', async ({ page }) => {
    // Navigate to Record tab
    await page.click('button:has-text("Record")');
    
    // Check microphone device selector
    const deviceSelect = page.locator('select');
    await expect(deviceSelect).toBeVisible();
    
    // Should have at least one option
    const options = page.locator('select option');
    const optionCount = await options.count();
    expect(optionCount).toBeGreaterThan(0);
    
    // Test selecting different device
    if (optionCount > 1) {
      await deviceSelect.selectOption({ index: 1 });
    }
  });

  test('audio level meters display', async ({ page }) => {
    // Navigate to Record tab
    await page.click('button:has-text("Record")');
    
    // Check for audio level meter elements
    await expect(page.locator('text=Therapist (Mic)')).toBeVisible();
    await expect(page.locator('text=Client (Loopback)')).toBeVisible();
    
    // Check for meter bars
    const meterBars = page.locator('[class*="bg-green-500"], [class*="bg-blue-500"]');
    const barCount = await meterBars.count();
    expect(barCount).toBeGreaterThanOrEqual(2); // At least two meters
  });

  test('transcription display works', async ({ page }) => {
    // Navigate to Record tab to see live transcription
    await page.click('button:has-text("Record")');
    
    // Check transcription panel on the right
    await expect(page.locator('h2:has-text("Live Transcription")')).toBeVisible();
    
    // Check view mode buttons
    await expect(page.locator('button:has-text("Two Lanes")')).toBeVisible();
    await expect(page.locator('button:has-text("Unified")')).toBeVisible();
    
    // Test switching view modes
    await page.click('button:has-text("Unified")');
    await expect(page.locator('button:has-text("Unified")')).toHaveClass(/bg-blue-500/);
    
    await page.click('button:has-text("Two Lanes")');
    await expect(page.locator('button:has-text("Two Lanes")')).toHaveClass(/bg-blue-500/);
    
    // Check for copy and download buttons
    await expect(page.locator('button:has-text("Copy All")')).toBeVisible();
    await expect(page.locator('button:has-text("Download")')).toBeVisible();
  });

  test('error states are handled gracefully', async ({ page }) => {
    // Test various error scenarios
    
    // Navigate to Review tab when no data available
    await page.click('button:has-text("Review")');
    
    // Should show appropriate message, not crash
    await expect(page.locator('h3:has-text("No PHI Data Available")')).toBeVisible();
    
    // Navigate to Note tab
    await page.click('button:has-text("Note")');
    
    // Should show setup wizard, not crash
    await expect(page.locator('h2:has-text("Session Setup")')).toBeVisible();
    
    // Navigate to Dashboard tab
    await page.click('button:has-text("Dashboard")');
    
    // Should show dashboard, not crash
    await expect(page.locator('h2:has-text("Live Dashboard")')).toBeVisible();
  });

  test('responsive layout works on different sizes', async ({ page }) => {
    // Test desktop layout
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.click('button:has-text("Record")');
    
    // Should show side-by-side layout
    const recordPanel = page.locator('text=Audio Recording').first();
    const transcriptionPanel = page.locator('text=Live Transcription').first();
    
    await expect(recordPanel).toBeVisible();
    await expect(transcriptionPanel).toBeVisible();
    
    // Test smaller viewport
    await page.setViewportSize({ width: 800, height: 600 });
    
    // Layout should still be functional
    await expect(recordPanel).toBeVisible();
  });
});