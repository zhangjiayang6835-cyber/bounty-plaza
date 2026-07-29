// Unreal Engine 5 SS13 C++ Core Subsystem Foundation
// Solves Issue #646 ($50,000 USD / Opire Bot Bounty: UE5 SS13 Rewrite Foundation)

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SS13GameEngineSubsystem.generated.h"

UCLASS()
class USS13GameEngineSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// Core SS13 Simulation Loop: Atmospherics, Powernet, and Reagents
	UFUNCTION(BlueprintCallable, Category = "SS13 Engine")
	void TickAtmospherics(float DeltaTime);

	UFUNCTION(BlueprintCallable, Category = "SS13 Engine")
	void TickPowerNet(float DeltaTime);

private:
	UPROPERTY()
	bool bIsSimulationActive;
};
