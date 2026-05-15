/**
 * Phase 4 Migration: Add app_key field to existing documents
 *
 * CRITICAL: Run this BEFORE deploying Phase 4 code
 *
 * This script adds the app_key field to all existing documents
 * that don't have it, ensuring backward compatibility.
 *
 * Default app_key for existing data: "mandirmitra"
 * (since existing MandirMitra is the primary legacy app)
 */

// Connect to MongoDB
// mongo mongodb://user:pass@host:port/sanmitra_dev

use sanmitra_dev;

// ============================================================================
// MIGRATION FUNCTIONS
// ============================================================================

function migrateCollection(collectionName, defaultAppKey = "mandirmitra") {
  const collection = db.getCollection(collectionName);

  print(`\n📋 Migrating collection: ${collectionName}`);
  print(`   Default app_key: ${defaultAppKey}`);

  // Count documents without app_key
  const docCount = collection.countDocuments({ app_key: { $exists: false } });
  print(`   Documents needing migration: ${docCount}`);

  if (docCount === 0) {
    print(`   ✅ No documents to migrate`);
    return { migrated: 0, skipped: 0, error: 0 };
  }

  // Add app_key to all documents missing it
  const result = collection.updateMany(
    { app_key: { $exists: false } },
    { $set: { app_key: defaultAppKey } }
  );

  print(`   ✅ Migrated: ${result.modifiedCount} documents`);
  print(`   ⏭️  Skipped: ${result.matchedCount - result.modifiedCount} documents`);

  return {
    migrated: result.modifiedCount,
    skipped: result.matchedCount - result.modifiedCount,
    error: 0
  };
}

// ============================================================================
// VERIFY LIVE DATA BEFORE MIGRATION
// ============================================================================

print("\n" + "=".repeat(80));
print("PHASE 4 MIGRATION: Add app_key to Existing Documents");
print("=".repeat(80));

print("\n📊 PRE-MIGRATION STATUS:");
print("-".repeat(80));

// Check MandirMitra collections
const mandirCollections = [
  "mandir_temples",
  "mandir_donations",
  "mandir_sevas",
  "mandir_devotees",
  "mandir_onboarding_events",
  "mandir_coa_mappings",
  "mandir_source_accounts",
];

let totalDocsToMigrate = 0;

for (const col of mandirCollections) {
  try {
    const count = db.getCollection(col).countDocuments({ app_key: { $exists: false } });
    if (count > 0) {
      print(`   ${col}: ${count} documents without app_key`);
      totalDocsToMigrate += count;
    }
  } catch (e) {
    print(`   ${col}: Collection doesn't exist (OK)`);
  }
}

print(`\n   TOTAL DOCUMENTS TO MIGRATE: ${totalDocsToMigrate}`);

// ============================================================================
// PERFORM MIGRATION
// ============================================================================

if (totalDocsToMigrate === 0) {
  print("\n✅ ALL COLLECTIONS ALREADY MIGRATED - No action needed");
  print("\nYou can safely deploy Phase 4 code now.");
} else {
  print("\n⚠️  MIGRATION STARTING...\n");
  print("-".repeat(80));

  const results = {};

  // Migrate each collection
  for (const col of mandirCollections) {
    try {
      results[col] = migrateCollection(col, "mandirmitra");
    } catch (e) {
      print(`   ❌ Error migrating ${col}: ${e.message}`);
      results[col] = { migrated: 0, skipped: 0, error: 1 };
    }
  }

  // ========================================================================
  // SUMMARY
  // ========================================================================

  print("\n" + "=".repeat(80));
  print("📊 MIGRATION SUMMARY");
  print("=".repeat(80));

  let totalMigrated = 0;
  let totalErrors = 0;

  for (const [col, result] of Object.entries(results)) {
    if (result.migrated > 0 || result.error > 0) {
      const status = result.error > 0 ? "❌" : "✅";
      print(`${status} ${col}: ${result.migrated} migrated, ${result.error} errors`);
      totalMigrated += result.migrated;
      totalErrors += result.error;
    }
  }

  print("-".repeat(80));
  print(`TOTAL MIGRATED: ${totalMigrated}`);
  print(`TOTAL ERRORS: ${totalErrors}`);

  if (totalErrors === 0) {
    print("\n✅ MIGRATION SUCCESSFUL - All existing data now has app_key field");
    print("   You can safely deploy Phase 4 code now.");
  } else {
    print("\n❌ MIGRATION FAILED - Some documents could not be migrated");
    print("   Do NOT deploy Phase 4 code until all errors are resolved.");
  }
}

// ============================================================================
// POST-MIGRATION VERIFICATION
// ============================================================================

print("\n" + "=".repeat(80));
print("🔍 POST-MIGRATION VERIFICATION");
print("=".repeat(80));

print("\nVerifying all critical collections have app_key:");

for (const col of mandirCollections) {
  try {
    const countWithout = db.getCollection(col).countDocuments({ app_key: { $exists: false } });
    const countWith = db.getCollection(col).countDocuments({ app_key: { $exists: true } });

    if (countWithout > 0) {
      print(`❌ ${col}: ${countWithout} documents STILL missing app_key`);
    } else if (countWith > 0) {
      print(`✅ ${col}: ${countWith} documents have app_key`);
    } else {
      print(`⏭️  ${col}: No documents (OK)`);
    }
  } catch (e) {
    print(`⏭️  ${col}: Collection doesn't exist (OK)`);
  }
}

print("\n" + "=".repeat(80));
print("✅ Migration script completed");
print("=".repeat(80));
print("\nNEXT STEPS:");
print("1. Review the summary above");
print("2. If ✅ all collections verified, you can deploy Phase 4");
print("3. If ❌ any errors, fix them before deploying");
print("4. After deployment, monitor live system for any issues");
print("\n");
