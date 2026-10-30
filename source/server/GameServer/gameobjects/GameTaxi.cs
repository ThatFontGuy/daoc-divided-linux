using DOL.AI.Brain;

namespace DOL.GS
{
	/// <summary>
	/// 
	/// </summary>
	public class GameTaxi : GameNPC
	{
		public GameTaxi() : base()
		{
			Model = 449;
			MaxSpeedBase = 650;
			Size = 50;
			Level = 55;
			Name = "horse";
			BlankBrain brain = new BlankBrain();
			SetOwnBrain(brain);
		}
		
		public GameTaxi(INpcTemplate templateid) : base(templateid)
		{
			BlankBrain brain = new BlankBrain();
			SetOwnBrain(brain);
		}

		public override bool IsVisibleToPlayers => true;

		/// <summary>The old horse mesh (monster models 413-450, horse01.nif) and the unsaddled horses, with the saddled
		/// horse of the current mount rig (classic_body01_mount_horse.nif) that live's stables use. Riders sit on
		/// that rig; on the old mesh the 1.130 client leaves them standing on the horse's back.</summary>
		private static readonly System.Collections.Generic.Dictionary<ushort, ushort> SaddledHorses = new()
		{
			[413] = 2173, [449] = 2173, [2179] = 2173,      // brown
			[414] = 2172, [450] = 2172, [2127] = 2172,      // black
			[447] = 2174, [448] = 2174, [2180] = 2174,      // white, speckled and grey
		};

		public static ushort RideableModel(ushort model) => SaddledHorses.TryGetValue(model, out ushort saddled) ? saddled : model;

		/// <summary>GM /taxitest spawn and delay: the model a new stable horse is created with, and the milliseconds
		/// before its rider is seated (400 normally).</summary>
		public static ushort? SpawnModelOverride { get; set; }
		public static int MountDelay { get; set; } = 400;

		// Stable horses keep their own model: the patched 1.130 game.dll (patch_class_slots.py, RIDE_ANIM_EDIT) seats riders
		// on the old mesh, and the classic client may lack the saddled rig. RideableModel lists the saddled equivalents to
		// try in game with /taxitest spawn <id>.
		public override bool AddToWorld()
		{
			if (SpawnModelOverride.HasValue)
				Model = SpawnModelOverride.Value;
			return base.AddToWorld();
		}

		public override int MAX_PASSENGERS
		{
			get
			{
				return 1;
			}
		}

		/// <summary>Seat number sent in the riding packet when set (GM /taxitest seat); 0 otherwise.</summary>
		public static int? SeatOverride { get; set; }

		/// <summary>Riding packet mount flag (normally 1) and its trailing 16-bit value (normally 0) for taxis, when set
		/// (GM /taxitest flag, /taxitest extra).</summary>
		public static byte? MountFlagOverride { get; set; }
		public static ushort? TrailingOverride { get; set; }

		public override int SLOT_OFFSET
		{
			get
			{
				return SeatOverride ?? 0;
			}
		}
	}
}
